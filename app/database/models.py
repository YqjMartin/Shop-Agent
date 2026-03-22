from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship


def utc_now():
    """返回当前UTC时间（时区感知）"""
    return datetime.now(timezone.utc)


Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=True)
    phone = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)
    hashed_password = Column(String(64), nullable=False)  # SHA256 哈希
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关联
    orders = relationship("Order", back_populates="user")


class Product(Base):
    """产品表"""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=True, index=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # 关联
    order_items = relationship("OrderItem", back_populates="product")


class Order(Base):
    """订单表"""
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)  # 订单号
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # 物流信息
    tracking_number = Column(String(50), nullable=True, index=True)  # 快递单号
    shipping_status = Column(String(20), default="pending", index=True)  # 物流状态
    shipping_address = Column(Text, nullable=True)

    # 订单状态
    status = Column(String(20), default="pending", index=True)  # pending, paid, shipped, delivered, cancelled

    # 金额
    total_amount = Column(Float, nullable=False, default=0.0)

    # 时间
    created_at = Column(DateTime, default=utc_now, index=True)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)
    shipped_at = Column(DateTime, nullable=True)  # 发货时间
    delivered_at = Column(DateTime, nullable=True)  # 收货时间

    # 关联
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    """订单商品表"""
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)

    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=False)  # 下单时的单价
    subtotal = Column(Float, nullable=False)  # 小计

    created_at = Column(DateTime, default=utc_now)

    # 关联
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
