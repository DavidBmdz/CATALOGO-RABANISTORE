"""Grafo no dirigido de productos que pueden combinarse."""

from collections import deque


class RecommendationGraph:
    # Relaciones de rutina entre categorías; cada producto también conecta
    # con los demás productos de su misma categoría.
    COMPATIBLE = {
        "rubores": {"rostro", "labios", "ojos", "correctores"},
        "correctores": {"rostro", "rubores"},
        "rostro": {"rubores", "correctores", "labios"},
        "labios": {"rostro", "rubores", "ojos"},
        "ojos": {"labios", "rubores"},
        "alcohol": set(),
    }

    def __init__(self, products):
        self.adjacency = {product["id"]: [] for product in products}
        for index, left in enumerate(products):
            for right in products[index + 1:]:
                same_category = left["cat"] == right["cat"]
                compatible = right["cat"] in self.COMPATIBLE.get(left["cat"], set())
                if same_category or compatible:
                    self._connect(left["id"], right["id"])

    def _connect(self, left, right):
        self.adjacency[left].append(right)
        self.adjacency[right].append(left)

    def recommend(self, product_id, limit=6):
        """BFS: devuelve productos cercanos, sin repetir el producto de origen."""
        if product_id not in self.adjacency:
            return []
        queue = deque([product_id])
        visited = {product_id}
        result = []
        while queue and len(result) < limit:
            current = queue.popleft()
            for neighbor in self.adjacency[current]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append(neighbor)
                    queue.append(neighbor)
                    if len(result) == limit:
                        break
        return result
