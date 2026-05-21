from datetime import date, datetime
from typing import Optional
from sqlalchemy import String, DateTime, ForeignKey, Date, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.backend.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")

class Actif(Base): 
    __tablename__ = "actifs"

    id: Mapped[int] = mapped_column(primary_key=True)
    isin_code: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    ticker_yfinance: Mapped[str] = mapped_column(String(255))
    nom_etf: Mapped[str] = mapped_column(String(255))
    
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="actif")
    historique_prix: Mapped[list["HistoriquePrix"]] = relationship(back_populates="actif")

class Transaction(Base): 
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    
    actif_id: Mapped[Optional[int]] = mapped_column(ForeignKey("actifs.id"), nullable=True)
    
    date: Mapped[date] = mapped_column(Date) # CORRECTION : juste "date"
    operation_type: Mapped[str] = mapped_column(String(255))  # Versement, Achat, Vente
    quantity: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    unit_price: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    fees: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)

    user: Mapped["User"] = relationship(back_populates="transactions")
    actif: Mapped[Optional["Actif"]] = relationship(back_populates="transactions")

class HistoriquePrix(Base):
    __tablename__ = "historique_prix"

    id: Mapped[int] = mapped_column(primary_key=True)
    actif_id: Mapped[int] = mapped_column(ForeignKey("actifs.id"))
    date: Mapped[date] = mapped_column(Date)
    prix: Mapped[float] = mapped_column(Numeric(10, 4))

    actif: Mapped["Actif"] = relationship(back_populates="historique_prix")