
class PurchaseProductDetail:
    def __init__(self, product_name=None, qty=None, entity=None, unit_price=None, description=None, details=None, sub_total=None, entity_obj=None):
        self.product_name = product_name
        self.qty = qty
        self.entity = entity
        self.unit_price = unit_price
        self.description = description
        self.details = details
        self.sub_total = sub_total
        self.entity_obj = entity_obj