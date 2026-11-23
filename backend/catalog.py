"""Servicio de catálogo que combina las estructuras del proyecto."""

import json
from pathlib import Path

from category_tree import CategoryTree
from doubly_linked_list import DoublyLinkedCart
from linked_list import SinglyLinkedHistory
from recommendation_graph import RecommendationGraph
from stack_queue import Queue, Stack


DATA_FILE = Path(__file__).with_name("products.json")


class CatalogStore:
    def __init__(self):
        self.products = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        self.products_by_id = {product["id"]: product for product in self.products}
        self.categories = CategoryTree(self.products)
        self.recommendations = RecommendationGraph(self.products)
        self.histories = {}
        self.undo_stacks = {}
        self.carts = {}
        self.pending_inquiries = Queue()

    def search(self, category=None, query=""):
        """Filtra el catálogo, que se almacena como una lista de Python."""
        allowed_ids = None
        if category and category != "all":
            allowed_ids = self.categories.product_ids(category)
            if allowed_ids is None:
                return []

        query = query.casefold().strip()
        result = []
        for product in self.products:
            if allowed_ids is not None and product["id"] not in allowed_ids:
                continue
            searchable = " ".join([
                product["name"], product["desc"],
                product["label"],
                " ".join(shade["name"] for shade in product["shades"]),
            ]).casefold()
            if not query or query in searchable:
                result.append(product)
        return result

    def get_product(self, product_id):
        # Diccionario/hash: consulta promedio O(1) por identificador.
        return self.products_by_id.get(product_id)

    def recommendations_for(self, product_id):
        return [
            self.products_by_id[item_id]
            for item_id in self.recommendations.recommend(product_id)
            if item_id in self.products_by_id
        ]

    def visit(self, session_id, product_id):
        history = self.histories.setdefault(session_id, SinglyLinkedHistory())
        history.visit(product_id)
        self.undo_stacks.setdefault(session_id, Stack()).push(product_id)
        return [self.products_by_id[item] for item in history.recent_ids()]

    def history(self, session_id):
        history = self.histories.get(session_id)
        if not history:
            return []
        return [self.products_by_id[item] for item in history.recent_ids()
                if item in self.products_by_id]

    def undo_visit(self, session_id):
        stack = self.undo_stacks.get(session_id)
        history = self.histories.get(session_id)
        product_id = stack.pop() if stack else None
        if product_id and history:
            history.remove_first(product_id)
        return self.history(session_id)

    def cart_items(self, session_id):
        cart = self.carts.get(session_id)
        return cart.items() if cart else []

    def add_to_cart(self, session_id, product_id, shade_name, quantity=1):
        product = self.get_product(product_id)
        if not product:
            raise ValueError("No existe ese producto.")
        shade = next((item for item in product["shades"]
                      if item["name"] == shade_name), None)
        if not shade:
            raise ValueError("El tono seleccionado no pertenece al producto.")
        try:
            quantity = max(1, min(int(quantity), 99))
        except (TypeError, ValueError):
            quantity = 1

        cart = self.carts.setdefault(session_id, DoublyLinkedCart())
        key = f"{product_id}|{shade_name}"
        node = cart.find(key)
        if node:
            node.item["quantity"] += quantity
        else:
            cart.append(key, {
                "key": key,
                "product_id": product_id,
                "name": product["name"],
                "shade": shade_name,
                "quantity": quantity,
                "unit_price": product["price"],
            })
        return self.cart_items(session_id)

    def remove_from_cart(self, session_id, key):
        cart = self.carts.get(session_id)
        node = cart.find(key) if cart else None
        if node:
            cart.remove_node(node)
        return self.cart_items(session_id)

    def record_inquiry(self, session_id, product_id, shade_name=""):
        product = self.get_product(product_id)
        if not product:
            raise ValueError("No existe ese producto.")
        inquiry = {
            "session": session_id,
            "product_id": product_id,
            "product_name": product["name"],
            "shade": shade_name,
        }
        self.pending_inquiries.enqueue(inquiry)
        return inquiry

    def next_inquiry(self):
        return self.pending_inquiries.dequeue()
