from abc import ABC, abstractmethod
from collections import deque


class MemoryAccessor:
    def __init__(self, pid: str, page_accesses: list[int]):
        self.pid = pid
        self.pages_count = max(page_accesses)
        self.accesses = [f"{pid}{page}" for page in page_accesses]
        self._idx = -1

    def __iter__(self):
        return self

    def __next__(self):
        self._idx += 1
        return self.accesses[self._idx] if self._idx < len(self.accesses) else None


class PageFault(Exception):
    pass


class PhysicsMemory(ABC):
    def __init__(self, size: int):
        self.size = size

    @abstractmethod
    def __str__(self):
        pass

    @abstractmethod
    def is_free(self) -> bool:
        pass

    @abstractmethod
    def use(self, page_id: str) -> None:
        pass

    @abstractmethod
    def swap(self) -> str:
        pass

    @abstractmethod
    def allocate(self, page_id: str) -> None:
        pass

    @abstractmethod
    def tick(self) -> None:
        pass


class GlobalOptMemory(PhysicsMemory):
    def __init__(self, accesses: list[str], size: int):
        super(GlobalOptMemory, self).__init__(size)

        self._accesses = accesses
        self._pages = set(self._accesses)
        self._page_pointer = -1
        self._memory = set()
        self._pointers_count = dict()

    def __str__(self):
        return str(dict((page, count) for page, count in self._pointers_count.items() if page in self._memory))

    def is_free(self) -> bool:
        return len(self._memory) < self.size

    def use(self, page_id: str) -> None:
        if page_id not in self._memory:
            raise PageFault()

    def swap(self) -> str:
        pointers_in_memory = [(page, count) for page, count in self._pointers_count.items() if page in self._memory]
        most_deferred_page = max(pointers_in_memory, key=lambda p: p[1])[0]

        self._memory.remove(most_deferred_page)

        return most_deferred_page

    def allocate(self, page_id: str) -> None:
        self._memory.add(page_id)

    def tick(self) -> None:
        self._page_pointer += 1
        for page_id in self._pages:
            try:
                next_idx = self._get_next_index(self._accesses, page_id, self._page_pointer)
                self._pointers_count[page_id] = next_idx - self._page_pointer
            except ValueError:
                self._pointers_count[page_id] = float("inf")

    @staticmethod
    def _get_next_index(pages: list[str], page_id: str, start: int) -> int:
        return pages.index(page_id, start)


class GlobalFifoMemory(PhysicsMemory):
    def __init__(self, size: int):
        super(GlobalFifoMemory, self).__init__(size)
        self._memory = deque()

    def __str__(self):
        return str(self._memory)

    def is_free(self) -> bool:
        return len(self._memory) < self.size

    def use(self, page_id: str) -> None:
        if page_id not in self._memory:
            raise PageFault()

    def swap(self) -> str:
        return self._memory.popleft()

    def allocate(self, page_id: str) -> None:
        self._memory.append(page_id)

    def tick(self) -> None:
        pass


class GlobalLfuMemory(PhysicsMemory):
    def __init__(self, size: int):
        super(GlobalLfuMemory, self).__init__(size)
        self._memory = dict()

    def __str__(self):
        return str(self._memory)

    def is_free(self) -> bool:
        return len(self._memory) < self.size

    def use(self, page_id: str) -> None:
        if page_id not in self._memory:
            raise PageFault()

        self._memory[page_id] += 1

    def swap(self) -> str:
        not_frequency_page = min(self._memory.items(), key=lambda p: p[1])[0]
        del self._memory[not_frequency_page]

        return not_frequency_page

    def allocate(self, page_id: str) -> None:
        self._memory[page_id] = 1

    def tick(self) -> None:
        pass


class GlobalLruMemory(PhysicsMemory):
    def __init__(self, size: int):
        super(GlobalLruMemory, self).__init__(size)
        self._memory = dict()

    def __str__(self):
        return str(self._memory)

    def is_free(self) -> bool:
        return len(self._memory) < self.size

    def use(self, page_id: str) -> None:
        if page_id not in self._memory:
            raise PageFault()

        self._memory[page_id] = 0

    def swap(self) -> str:
        old_page = max(self._memory.items(), key=lambda p: p[1])[0]
        del self._memory[old_page]

        return old_page

    def allocate(self, page_id: str) -> None:
        self._memory[page_id] = 0

    def tick(self) -> None:
        for page in self._memory.keys():
            self._memory[page] += 1


def simulate(accessors: list[MemoryAccessor], memory: PhysicsMemory):
    print(memory.__class__.__name__)
    page_fault_count = 0
    finished_accessors = set()

    while len(finished_accessors) < len(accessors):
        for accessor in filter(lambda accessor_: accessor_ not in finished_accessors, accessors):
            page_id: str = next(accessor)

            if page_id is None:
                finished_accessors.add(accessor)
                continue

            print(f"{page_id} -> ", end="")

            memory.tick()

            if memory.is_free():
                memory.allocate(page_id)
                continue

            try:
                memory.use(page_id)
                print(memory)
            except PageFault:
                print(memory, "= PAGE FAULT -> ", end="")

                page_fault_count += 1
                swapped_page = memory.swap()
                memory.allocate(page_id)

                print(swapped_page)

    print(f"PAGE FAULTS: {page_fault_count}\n")


def get_accessor_from_name(pid: str, name_in: str) -> MemoryAccessor:
    alphabet = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"

    parsed = _, name, _ = name_in.lower().split()
    full_name = "".join(parsed)

    pages_count = len(name)
    pages = list(filter(lambda v: v > 0, ((alphabet.index(alpha) + 1) % pages_count for alpha in full_name)))

    return MemoryAccessor(pid, pages)


def get_row_vector_accesses_from_accessors(accessors: list[MemoryAccessor]) -> list[str]:
    vector = list()
    finished_accessors = set()

    while len(finished_accessors) < len(accessors):
        for accessor in filter(lambda accessor_: accessor_ not in finished_accessors, accessors):
            page_id: str = next(accessor)

            if page_id is None:
                finished_accessors.add(accessor)
                continue

            vector.append(page_id)

    return vector


def get_accessors(prev_name: str, name: str, next_name: str) -> list[MemoryAccessor]:
    return [
        get_accessor_from_name("A", prev_name),
        get_accessor_from_name("B", name),
        get_accessor_from_name("C", next_name)
    ]


def main():
    prev_name, name, next_name = (input() for _ in range(3))

    memory_size = 10
    memories = [
        GlobalOptMemory(get_row_vector_accesses_from_accessors(get_accessors(prev_name, name, next_name)), memory_size),
        GlobalFifoMemory(memory_size),
        GlobalLfuMemory(memory_size),
        GlobalLruMemory(memory_size)
    ]

    for memory in memories:
        simulate(get_accessors(prev_name, name, next_name), memory)


if __name__ == "__main__":
    main()
