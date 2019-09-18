import base64 

from sqlalchemy import Column, String, LargeBinary
from sqlalchemy.orm import Session, relationship
from sqlalchemy.ext.hybrid import hybrid_property 
from sqlalchemy.orm.exc import NoResultFound

from .base import Base, Database
from .member import Member
from .collaboration import Collaboration
from .user import User


class Organization(Base):
    """A legal entity.
    
    An organization plays a central role in managing distributed tasks. Each
    Organization contains a public key which other organizations can use to 
    send encrypted messages that only this organization can read.
    """

    # fields
    name = Column(String)
    domain = Column(String)
    address1 = Column(String)
    address2 = Column(String)
    zipcode = Column(String)
    country = Column(String)
    _public_key = Column(LargeBinary)

    # relations
    collaborations = relationship("Collaboration", secondary="Member",
        back_populates="organizations")
    results = relationship("Result", back_populates="organization")
    nodes = relationship("Node", back_populates="organization")
    users = relationship("User", back_populates="organization")
    created_tasks = relationship("Task", back_populates="initiator")

    @classmethod
    def get_by_name(cls, name):
        session = Database().Session
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None

    @hybrid_property
    def public_key(self):
        return base64.encodebytes(self._public_key).encode("ascii")

    @public_key.setter
    def public_key(self, public_key_b64):
        """Assumes that the public key is in b64-encoded."""
        self._public_key = base64.b64decode(public_key_b64).decode("ascii")

    def __repr__(self):
        number_of_users = len(self.users)
        return ("<Organization "
            f"name:{self.name}, "
            f"domain:{self.domain}, "
            f"users:{number_of_users}"
        ">")
