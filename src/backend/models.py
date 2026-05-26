from datetime import date, datetime
from typing import Optional
from sqlalchemy import Column, String, DateTime, ForeignKey, Date, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import os 
import hashlib
from src.backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    salt: Mapped[str] = mapped_column(String(255), nullable=True)  
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    
    mfa_secret: Mapped[str] = mapped_column(String(255), nullable=True)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    mfa_type: Mapped[str] = mapped_column(String(50), default="NONE")

    email_otp_code: Mapped[str] = mapped_column(String(6), nullable=True)
    email_otp_expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    fichiers_importes: Mapped[list["FichierImporte"]] = relationship(back_populates="user")

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

class FichierImporte(Base):
    __tablename__ = "fichiers_importes"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    nom_fichier: Mapped[str] = mapped_column(String(255))
    hash_md5: Mapped[str] = mapped_column(String(64), index=True)
    date_import: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    user: Mapped["User"] = relationship(back_populates="fichiers_importes")