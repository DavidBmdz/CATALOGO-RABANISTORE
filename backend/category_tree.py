"""Árbol de categorías del catálogo."""


class CategoryNode:
    def __init__(self, name, category_id=None):
        self.name = name
        self.category_id = category_id
        self.product_ids = []
        self.children = {}

    def to_dict(self):
        children = [child.to_dict() for child in self.children.values()]
        return {
            "name": self.name,
            "category": self.category_id,
            "product_count": len(self.product_ids) + sum(
                child["product_count"] for child in children
            ),
            "children": children,
        }


class CategoryTree:
    # Cada categoría comercial se ubica bajo una familia del árbol.
    PATHS = {
        "rostro": ("Maquillaje", "Rostro"),
        "rubores": ("Maquillaje", "Rostro", "Rubores"),
        "correctores": ("Maquillaje", "Rostro", "Correctores"),
        "labios": ("Maquillaje", "Labios"),
        "ojos": ("Maquillaje", "Ojos"),
        "alcohol": ("Cuidado personal", "Sanitizantes"),
    }

    def __init__(self, products):
        self.root = CategoryNode("Catálogo")
        self.nodes_by_category = {}
        for product in products:
            category = product["cat"]
            path = self.PATHS.get(category, ("Otros", product["label"]))
            node = self.root
            for name in path:
                node = node.children.setdefault(name, CategoryNode(name))
            node.category_id = category
            node.product_ids.append(product["id"])
            self.nodes_by_category[category] = node

    def filters(self):
        """Categorías que tienen productos, en orden de creación del árbol."""
        result = []

        def visit(node):
            if node.category_id:
                result.append({"id": node.category_id, "label": node.name})
            for child in node.children.values():
                visit(child)

        visit(self.root)
        return result

    def product_ids(self, category):
        node = self.nodes_by_category.get(category)
        if not node:
            return None
        result = []

        def collect(current):
            result.extend(current.product_ids)
            for child in current.children.values():
                collect(child)

        collect(node)
        return set(result)

    def as_dict(self):
        return self.root.to_dict()
