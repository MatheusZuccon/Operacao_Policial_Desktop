from dataclasses import dataclass, field
from typing import Optional


@dataclass
class WeaponModel:
    weapon: str
    quantity: int


@dataclass
class VehicleModel:
    brand: str
    model: str
    plate: str
    armored: bool = False


@dataclass
class RoleModel:
    role: str
    quantity: int
    officers: list[str] = field(default_factory=list)


@dataclass
class EquipmentModel:
    equipment: str
    quantity: int


@dataclass
class OperationModel:
    id: Optional[int] = None
    operation_number: Optional[str] = None
    name: str = ""
    operation_type: str = ""
    location: str = ""
    description: str = ""
    created_at: Optional[str] = None
    weapons: list[WeaponModel] = field(default_factory=list)
    vehicles: list[VehicleModel] = field(default_factory=list)
    roles: list[RoleModel] = field(default_factory=list)
    investigation_equipments: list[EquipmentModel] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "OperationModel":
        return cls(
            id=data.get("id"),
            operation_number=data.get("operation_number"),
            name=data.get("name", ""),
            operation_type=data.get("operation_type", ""),
            location=data.get("location", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at"),
            weapons=[
                WeaponModel(weapon=w["weapon"], quantity=w.get("quantity", 1))
                for w in data.get("weapons", [])
            ],
            vehicles=[
                VehicleModel(
                    brand=v.get("brand", ""),
                    model=v.get("model", ""),
                    plate=v.get("plate", ""),
                    armored=v.get("armored", False)
                )
                for v in data.get("vehicles", [])
            ],
            roles=[
                RoleModel(
                    role=r["role"],
                    quantity=r.get("quantity", 1),
                    officers=r.get("officers", [])
                )
                for r in data.get("roles", [])
            ],
            investigation_equipments=[
                EquipmentModel(
                    equipment=e["equipment"],
                    quantity=e.get("quantity", 1)
                )
                for e in data.get("investigation_equipments", [])
            ],
        )

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "operation_type": self.operation_type,
            "location": self.location,
            "description": self.description,
            "weapons": [
                {"weapon": w.weapon, "quantity": w.quantity}
                for w in self.weapons
            ],
            "vehicles": [
                {
                    "brand": v.brand,
                    "model": v.model,
                    "plate": v.plate,
                    "armored": v.armored
                }
                for v in self.vehicles
            ],
            "roles": [
                {
                    "role": r.role,
                    "quantity": r.quantity,
                    "officers": r.officers
                }
                for r in self.roles
            ],
            "investigation_equipments": [
                {"equipment": e.equipment, "quantity": e.quantity}
                for e in self.investigation_equipments
            ],
        }
