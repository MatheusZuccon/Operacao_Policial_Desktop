from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VehicleModel:
    name: str
    armored: bool = False
    id: Optional[int] = None
    operation_id: Optional[int] = None


@dataclass
class OperationModel:
    id: Optional[int] = None
    name: str = ""
    operation_type: str = ""
    location: str = ""
    description: str = ""
    created_at: Optional[str] = None
    weapons: list[str] = field(default_factory=list)
    vehicles: list[VehicleModel] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    investigation_equipments: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "OperationModel":
        return cls(
            id=data.get("id"),
            name=data.get("name", ""),
            operation_type=data.get("operation_type", ""),
            location=data.get("location", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at"),
            weapons=[w["name"] for w in data.get("weapons", [])],
            vehicles=[
                VehicleModel(name=v["name"], armored=v.get("armored", False), id=v.get("id"))
                for v in data.get("vehicles", [])
            ],
            roles=[r["name"] for r in data.get("roles", [])],
            investigation_equipments=[e["name"] for e in data.get("investigation_equipments", [])],
        )

    def to_payload(self) -> dict:
        return {
            "name": self.name,
            "operation_type": self.operation_type,
            "location": self.location,
            "description": self.description,
            "weapons": self.weapons,
            "vehicles": [{"name": v.name, "armored": v.armored} for v in self.vehicles],
            "roles": self.roles,
            "investigation_equipments": self.investigation_equipments,
        }
