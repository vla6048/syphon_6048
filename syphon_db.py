from typing import Optional
import datetime

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKeyConstraint, Index, Integer, String, TIMESTAMP, Table
from sqlalchemy.dialects.mysql import INTEGER, TINYINT
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass


class BdcomList(Base):
    __tablename__ = 'bdcom_list'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ntst_id: Mapped[Optional[int]] = mapped_column(Integer)
    ip: Mapped[Optional[str]] = mapped_column(String(15))
    login: Mapped[Optional[str]] = mapped_column(String(150))
    passwd: Mapped[Optional[str]] = mapped_column(String(150))


class Devices(Base):
    __tablename__ = 'devices'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    ip_address: Mapped[str] = mapped_column(String(15), nullable=False)
    device_type: Mapped[str] = mapped_column(Enum('power_control', 'generator_control'), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    power_control: Mapped[list['Devices']] = relationship('Devices', secondary='device_relations', primaryjoin=lambda: Devices.id == t_device_relations.c.generator_control_id, secondaryjoin=lambda: Devices.id == t_device_relations.c.power_control_id, back_populates='generator_control')
    generator_control: Mapped[list['Devices']] = relationship('Devices', secondary='device_relations', primaryjoin=lambda: Devices.id == t_device_relations.c.power_control_id, secondaryjoin=lambda: Devices.id == t_device_relations.c.generator_control_id, back_populates='power_control')


class FetchInfo(Base):
    __tablename__ = 'fetch_info'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    db: Mapped[Optional[str]] = mapped_column(String(100))
    db_table: Mapped[Optional[str]] = mapped_column(String(100))
    modification_time: Mapped[Optional[datetime.date]] = mapped_column(Date)


class NtstLogs(Base):
    __tablename__ = 'ntst_logs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    log_date: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime)
    ip: Mapped[Optional[str]] = mapped_column(String(15))
    canton: Mapped[Optional[str]] = mapped_column(String(50))
    model: Mapped[Optional[str]] = mapped_column(String(150))
    sw_rank: Mapped[Optional[int]] = mapped_column(TINYINT)


class NtstPingerHostsLog(Base):
    __tablename__ = 'ntst_pinger_hosts_log'

    id: Mapped[int] = mapped_column(INTEGER, primary_key=True)
    ip: Mapped[str] = mapped_column(String(50), nullable=False)
    stop: Mapped[datetime.datetime] = mapped_column(TIMESTAMP, nullable=False)
    start: Mapped[Optional[datetime.datetime]] = mapped_column(TIMESTAMP)
    downtime: Mapped[Optional[int]] = mapped_column(Integer)


class SwitchesReport(Base):
    __tablename__ = 'switches_report'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canton: Mapped[Optional[str]] = mapped_column(String(100))
    model: Mapped[Optional[str]] = mapped_column(String(100))
    ip: Mapped[Optional[str]] = mapped_column(String(15))
    switch_rank: Mapped[Optional[int]] = mapped_column(TINYINT)
    vetka: Mapped[Optional[int]] = mapped_column(Integer)


t_device_relations = Table(
    'device_relations', Base.metadata,
    Column('power_control_id', Integer, primary_key=True),
    Column('generator_control_id', Integer, primary_key=True),
    ForeignKeyConstraint(['generator_control_id'], ['devices.id'], ondelete='CASCADE', name='device_relations_ibfk_2'),
    ForeignKeyConstraint(['power_control_id'], ['devices.id'], ondelete='CASCADE', name='device_relations_ibfk_1'),
    Index('generator_control_id', 'generator_control_id')
)
