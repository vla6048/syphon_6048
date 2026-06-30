from typing import Optional
import datetime

from sqlalchemy import Date, Float, ForeignKeyConstraint, Index, Integer, String, Text, text
from sqlalchemy.dialects.mysql import BIGINT, FLOAT, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class FopCredentials(Base):
    __tablename__ = 'fop_credentials'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    pidstava: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    iban: Mapped[Optional[str]] = mapped_column(String(255))
    bank_account_detail: Mapped[Optional[str]] = mapped_column(String(255))
    name_short: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(100))

    agreements: Mapped[list['Agreements']] = relationship('Agreements', back_populates='master')
    fop_territory: Mapped[list['FopTerritory']] = relationship('FopTerritory', back_populates='master')


class LlcCredentials(Base):
    __tablename__ = 'llc_credentials'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    in_persona: Mapped[Optional[str]] = mapped_column(String(255))
    edrpou: Mapped[Optional[int]] = mapped_column(BIGINT)
    inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    address: Mapped[Optional[str]] = mapped_column(String(255))
    iban: Mapped[Optional[str]] = mapped_column(String(255))
    bank_account_detail: Mapped[Optional[str]] = mapped_column(String(255))
    name_short: Mapped[Optional[str]] = mapped_column(String(255))
    canton: Mapped[Optional[str]] = mapped_column(String(255))

    llc_agreements: Mapped[list['LlcAgreements']] = relationship('LlcAgreements', back_populates='llc')
    llc_cantons: Mapped[list['LlcCantons']] = relationship('LlcCantons', back_populates='llc')


class ProtocolsMissingAgreements(Base):
    __tablename__ = 'protocols_missing_agreements'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clientId: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    fop_inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    fop_name: Mapped[Optional[str]] = mapped_column(String(255))
    fop_in: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    fop_change: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    fop_expense: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    fop_out: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    type_agr: Mapped[Optional[str]] = mapped_column(String(255))
    ri_inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    ri_name: Mapped[Optional[str]] = mapped_column(String(255))
    date_of_protocol: Mapped[Optional[datetime.date]] = mapped_column(Date)
    agreement_state: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'0'"))


class ProtocolsTest(Base):
    __tablename__ = 'protocols_test'
    __table_args__ = (
        Index('agreement', 'agreement'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agreement: Mapped[int] = mapped_column(Integer, nullable=False)
    proto_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    proto_sum: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    proto_sum_caps: Mapped[Optional[str]] = mapped_column(String(255))
    proto_state: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))


class RiCredentials(Base):
    __tablename__ = 'ri_credentials'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String(255))
    inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    pidstava: Mapped[Optional[str]] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    iban: Mapped[Optional[str]] = mapped_column(String(255))
    bank_account_detail: Mapped[Optional[str]] = mapped_column(String(255))
    name_short: Mapped[Optional[str]] = mapped_column(String(255))
    email: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(13))

    agreements: Mapped[list['Agreements']] = relationship('Agreements', back_populates='ri')
    engineer_cantons: Mapped[list['EngineerCantons']] = relationship('EngineerCantons', back_populates='engineer')
    llc_agreements: Mapped[list['LlcAgreements']] = relationship('LlcAgreements', back_populates='ri')


class SoftEstimates(Base):
    __tablename__ = 'soft_estimates'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clientId: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    fop_inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    fop_name: Mapped[Optional[str]] = mapped_column(String(255))
    fop_in: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    fop_change: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    fop_expense: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    fop_out: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    type_agr: Mapped[Optional[str]] = mapped_column(String(255))
    ri_inn: Mapped[Optional[int]] = mapped_column(BIGINT)
    ri_name: Mapped[Optional[str]] = mapped_column(String(255))
    date_of_protocol: Mapped[Optional[datetime.date]] = mapped_column(Date)


class Agreements(Base):
    __tablename__ = 'agreements'
    __table_args__ = (
        ForeignKeyConstraint(['master_id'], ['fop_credentials.id'], ondelete='CASCADE', name='agreements_ibfk_1'),
        ForeignKeyConstraint(['ri_id'], ['ri_credentials.id'], ondelete='CASCADE', name='agreements_ibfk_2'),
        Index('master_id', 'master_id'),
        Index('ri_id', 'ri_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ri_id: Mapped[int] = mapped_column(Integer, nullable=False)
    agreement_name: Mapped[Optional[str]] = mapped_column(String(255))
    agreement_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    agreement_state: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    master: Mapped['FopCredentials'] = relationship('FopCredentials', back_populates='agreements')
    ri: Mapped['RiCredentials'] = relationship('RiCredentials', back_populates='agreements')
    agreement_termination: Mapped[list['AgreementTermination']] = relationship('AgreementTermination', back_populates='agreement')
    protocols: Mapped[list['Protocols']] = relationship('Protocols', back_populates='agreements')


class EngineerCantons(Base):
    __tablename__ = 'engineer_cantons'
    __table_args__ = (
        ForeignKeyConstraint(['engineer_id'], ['ri_credentials.id'], ondelete='CASCADE', name='engineer_cantons_ibfk_1'),
        Index('engineer_id', 'engineer_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    engineer_id: Mapped[Optional[int]] = mapped_column(Integer)
    canton: Mapped[Optional[str]] = mapped_column(String(100))

    engineer: Mapped[Optional['RiCredentials']] = relationship('RiCredentials', back_populates='engineer_cantons')


class FopTerritory(Base):
    __tablename__ = 'fop_territory'
    __table_args__ = (
        ForeignKeyConstraint(['master_id'], ['fop_credentials.id'], ondelete='CASCADE', onupdate='CASCADE', name='fop_territory_ibfk_1'),
        Index('master_id', 'master_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    master_id: Mapped[int] = mapped_column(Integer, nullable=False)
    canton: Mapped[str] = mapped_column(String(255), nullable=False)
    vetka: Mapped[int] = mapped_column(Integer, nullable=False)
    transition: Mapped[Optional[datetime.date]] = mapped_column(Date)

    master: Mapped['FopCredentials'] = relationship('FopCredentials', back_populates='fop_territory')


class LlcAgreements(Base):
    __tablename__ = 'llc_agreements'
    __table_args__ = (
        ForeignKeyConstraint(['llc_id'], ['llc_credentials.id'], ondelete='CASCADE', name='llc_agreements_ibfk_1'),
        ForeignKeyConstraint(['ri_id'], ['ri_credentials.id'], ondelete='CASCADE', name='llc_agreements_ibfk_2'),
        Index('llc_id', 'llc_id'),
        Index('ri_id', 'ri_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    llc_id: Mapped[int] = mapped_column(Integer, nullable=False)
    ri_id: Mapped[int] = mapped_column(Integer, nullable=False)
    agreement_name: Mapped[Optional[str]] = mapped_column(String(255))
    agreement_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    agreement_state: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    llc: Mapped['LlcCredentials'] = relationship('LlcCredentials', back_populates='llc_agreements')
    ri: Mapped['RiCredentials'] = relationship('RiCredentials', back_populates='llc_agreements')
    llc_acts: Mapped[list['LlcActs']] = relationship('LlcActs', back_populates='llc_agreements')


class LlcCantons(Base):
    __tablename__ = 'llc_cantons'
    __table_args__ = (
        ForeignKeyConstraint(['llc_id'], ['llc_credentials.id'], ondelete='CASCADE', name='llc_cantons_ibfk_1'),
        Index('llc_id', 'llc_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    llc_id: Mapped[Optional[int]] = mapped_column(Integer)
    canton: Mapped[Optional[str]] = mapped_column(String(100))

    llc: Mapped[Optional['LlcCredentials']] = relationship('LlcCredentials', back_populates='llc_cantons')


class AgreementTermination(Base):
    __tablename__ = 'agreement_termination'
    __table_args__ = (
        ForeignKeyConstraint(['agreement_id'], ['agreements.id'], ondelete='CASCADE', name='agreement_termination_ibfk_1'),
        Index('agreement_id', 'agreement_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agreement_id: Mapped[int] = mapped_column(Integer, nullable=False)
    termination_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)

    agreement: Mapped['Agreements'] = relationship('Agreements', back_populates='agreement_termination')


class LlcActs(Base):
    __tablename__ = 'llc_acts'
    __table_args__ = (
        ForeignKeyConstraint(['agreement'], ['llc_agreements.id'], ondelete='CASCADE', name='llc_acts_ibfk_1'),
        Index('agreement', 'agreement')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agreement: Mapped[int] = mapped_column(Integer, nullable=False)
    act_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    act_sum: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    act_state: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    llc_agreements: Mapped['LlcAgreements'] = relationship('LlcAgreements', back_populates='llc_acts')
    llc_acts_data: Mapped[list['LlcActsData']] = relationship('LlcActsData', back_populates='act')


class Protocols(Base):
    __tablename__ = 'protocols'
    __table_args__ = (
        ForeignKeyConstraint(['agreement'], ['agreements.id'], ondelete='CASCADE', name='protocols_ibfk_1'),
        Index('agreement', 'agreement')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    agreement: Mapped[int] = mapped_column(Integer, nullable=False)
    proto_date: Mapped[Optional[datetime.date]] = mapped_column(Date)
    proto_sum: Mapped[Optional[float]] = mapped_column(FLOAT(100, 2))
    proto_sum_caps: Mapped[Optional[str]] = mapped_column(String(255))
    proto_state: Mapped[Optional[int]] = mapped_column(TINYINT(1), server_default=text("'1'"))

    agreements: Mapped['Agreements'] = relationship('Agreements', back_populates='protocols')


class LlcActsData(Base):
    __tablename__ = 'llc_acts_data'
    __table_args__ = (
        ForeignKeyConstraint(['act_id'], ['llc_acts.id'], ondelete='CASCADE', name='llc_acts_data_ibfk_1'),
        Index('act_id', 'act_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    act_id: Mapped[Optional[int]] = mapped_column(Integer)
    sw_rank: Mapped[Optional[int]] = mapped_column(TINYINT)
    model_list: Mapped[Optional[str]] = mapped_column(Text)
    count_devices: Mapped[Optional[int]] = mapped_column(Integer)
    ip_list: Mapped[Optional[str]] = mapped_column(Text)
    worktime_float: Mapped[Optional[float]] = mapped_column(Float)

    act: Mapped[Optional['LlcActs']] = relationship('LlcActs', back_populates='llc_acts_data')
