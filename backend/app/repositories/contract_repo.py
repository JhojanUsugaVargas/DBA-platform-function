"""Contract and Instance Repository."""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.contract import Contract, Instance
from app.core.security import encrypt_data, decrypt_data


def get_active_contracts(db: Session) -> List[Dict[str, Any]]:
    """Return all active contracts as dictionaries."""
    contracts = db.query(Contract).filter(Contract.is_active == True).all()
    return [{"id": c.id, "name": c.name} for c in contracts]


def add_contract(db: Session, name: str) -> Dict[str, Any]:
    """Create a new contract and return representation."""
    contract = Contract(name=name, is_active=True)
    db.add(contract)
    db.commit()
    db.refresh(contract)
    return {"id": contract.id, "name": contract.name, "is_active": contract.is_active}


def get_instances_by_contract(db: Session, contract_id: int) -> List[Dict[str, Any]]:
    """Return active instances for a contract."""
    instances = db.query(Instance).filter(
        Instance.contract_id == contract_id,
        Instance.is_active == True
    ).all()
    return [
        {
            "id": i.id,
            "name": i.name,
            "conn_str": decrypt_data(i.conn_str)
        }
        for i in instances
    ]


def get_instance_by_id(db: Session, instance_id: int) -> Optional[Instance]:
    """Retrieve an instance by ID."""
    return db.query(Instance).filter(Instance.id == instance_id).first()


def add_instance(db: Session, contract_id: int, name: str, conn_str: str) -> Instance:
    """Create an instance with its encrypted connection string."""
    encrypted_conn = encrypt_data(conn_str)
    new_instance = Instance(
        contract_id=contract_id,
        name=name,
        conn_str=encrypted_conn,
        is_active=True
    )
    db.add(new_instance)
    db.commit()
    db.refresh(new_instance)
    return new_instance
