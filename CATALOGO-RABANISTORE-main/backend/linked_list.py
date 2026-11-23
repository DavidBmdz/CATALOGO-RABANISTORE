"""Lista enlazada simple para el historial de productos vistos."""


class Node:
    def __init__(self, value, next_node=None):
        self.value = value
        self.next = next_node


class SinglyLinkedHistory:
    def __init__(self):
        self.head = None
        self.size = 0

    def visit(self, product_id):
        """Inserta una visita reciente al inicio: O(1)."""
        self.head = Node(product_id, self.head)
        self.size += 1

    def remove_first(self, product_id):
        """Elimina la primera visita coincidente: O(n)."""
        previous = None
        current = self.head
        while current:
            if current.value == product_id:
                if previous:
                    previous.next = current.next
                else:
                    self.head = current.next
                self.size -= 1
                return True
            previous, current = current, current.next
        return False

    def recent_ids(self, limit=8):
        result = []
        current = self.head
        while current and len(result) < limit:
            result.append(current.value)
            current = current.next
        return result
