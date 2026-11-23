"""Lista doblemente enlazada usada para las líneas de la bolsa/carrito."""


class CartNode:
    def __init__(self, key, item):
        self.key = key
        self.item = item
        self.previous = None
        self.next = None


class DoublyLinkedCart:
    def __init__(self):
        self.head = None
        self.tail = None
        self.size = 0

    def find(self, key):
        current = self.head
        while current:
            if current.key == key:
                return current
            current = current.next
        return None

    def append(self, key, item):
        node = CartNode(key, item)
        if self.tail:
            node.previous = self.tail
            self.tail.next = node
        else:
            self.head = node
        self.tail = node
        self.size += 1
        return node

    def remove_node(self, node):
        if node.previous:
            node.previous.next = node.next
        else:
            self.head = node.next
        if node.next:
            node.next.previous = node.previous
        else:
            self.tail = node.previous
        self.size -= 1

    def items(self):
        result = []
        current = self.head
        while current:
            result.append(current.item)
            current = current.next
        return result
