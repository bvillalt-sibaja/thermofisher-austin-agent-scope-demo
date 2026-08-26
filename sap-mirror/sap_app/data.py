import json
import os

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


class DemoData:
    """In-memory dummy data store, reset on every app restart."""

    def __init__(self):
        with open(os.path.join(_DATA_DIR, "materials.json")) as f:
            self.materials = json.load(f)
        self.production_orders = {}
        self._next_order_num = 411050
        self._seed_existing_orders()

    def _seed_existing_orders(self):
        """Matches the recording's real structure: material A35989C is
        reviewed via an EXISTING production order already in the system
        (Material Document List / Component Overview / "Review an other
        component?" loop) -- unlike A42362, which gets a brand-new order
        created live in the recording (Production Order Create). Without
        this, Material Document List has nothing to find for A35989C since
        `create_production_order` was never called for it."""
        order_no = "410892"
        order = {
            "order_no": order_no,
            "material": "A35989C",
            "item_category": "L",
            "total_quant": "5000",
            "long_text_create": "WIP order - filling line component.",
            "long_text_change": "",
            "start_date": "8/10/2026",
            "finish_date": "8/28/2026",
            "batch": "B26A3598",
            "status": "Released",
            "released": True,
            "saved": True,
        }
        self.production_orders[order_no] = order
        self.materials["A35989C"]["production_order"] = order_no

    def get_material(self, mat_no):
        mat_no = (mat_no or "").strip()
        return self.materials.get(mat_no)

    def create_production_order(self, material_no, item_category, total_quant, long_text_create,
                                 start_date, finish_date):
        order_no = str(self._next_order_num)
        self._next_order_num += 1
        order = {
            "order_no": order_no,
            "material": material_no,
            "item_category": item_category,
            "total_quant": total_quant,
            "long_text_create": long_text_create,
            "long_text_change": "",
            "start_date": start_date,
            "finish_date": finish_date,
            "batch": None,
            "status": "Created",
            "released": False,
            "saved": False,
        }
        self.production_orders[order_no] = order
        mat = self.get_material(material_no)
        if mat:
            mat["production_order"] = order_no
        return order

    def get_order(self, order_no):
        return self.production_orders.get((order_no or "").strip())

    def find_orders_by_material(self, material_no):
        return [o for o in self.production_orders.values() if o["material"] == (material_no or "").strip()]
