"""初始化示例数据脚本"""
import sys
sys.path.insert(0, ".")

from datetime import datetime, timedelta, timezone
from app.database import SessionLocal, init_db, drop_db
from app.database.models import User, Product, Order, OrderItem
from app.core.security import hash_password


def create_sample_data():
    """创建示例数据（完整重建数据库）"""
    print("=" * 50)
    print("开始初始化数据库...")
    print("=" * 50)

    # 重新创建所有表（确保 schema 最新）
    print("删除旧表...")
    drop_db()
    print("创建新表...")
    init_db()
    print("数据库表结构已创建")

    db = SessionLocal()

    try:
        # 检查是否已有数据
        existing_users = db.query(User).count()
        if existing_users > 0:
            print(f"数据库已有数据（{existing_users}个用户），跳过初始化")
            return

        # 创建用户（带密码哈希，示例用户密码为 "password123"）
        users = [
            User(
                username="zhangsan",
                email="zhangsan@example.com",
                phone="13800138000",
                address="北京市朝阳区",
                hashed_password=hash_password("password123")
            ),
            User(
                username="lisi",
                email="lisi@example.com",
                phone="13900139000",
                address="上海市浦东新区",
                hashed_password=hash_password("password123")
            ),
            User(
                username="wangwu",
                email="wangwu@example.com",
                phone="13700137000",
                address="广州市天河区",
                hashed_password=hash_password("password123")
            ),
        ]
        db.add_all(users)
        db.commit()
        print(f"创建了 {len(users)} 个用户")

        # 创建产品
        products = [
            Product(name="机械键盘", description="青轴机械键盘 RGB灯效 游戏键盘", category="电子产品", price=299.0, stock=50),
            Product(name="无线鼠标", description="无线蓝牙鼠标 静音设计 便携", category="电子产品", price=129.0, stock=100),
            Product(name="显示器", description="27寸4K显示器 IPS面板", category="电子产品", price=1999.0, stock=30),
            Product(name="耳机", description="降噪蓝牙耳机 续航30小时", category="电子产品", price=599.0, stock=80),
            Product(name="笔记本电脑", description="15.6寸轻薄本 16G+512G", category="电子产品", price=5999.0, stock=20),
            Product(name="移动硬盘", description="1TB移动硬盘 USB3.0", category="电子产品", price=399.0, stock=60),
            Product(name="键盘", description="有线键盘 104键", category="电子产品", price=89.0, stock=150),
            Product(name="鼠标垫", description="超大鼠标垫 防水防滑", category="配件", price=29.0, stock=200),
        ]
        db.add_all(products)
        db.commit()
        print(f"创建了 {len(products)} 个产品")

        # 创建订单
        now = datetime.now(timezone.utc)

        orders = [
            # 张三的订单
            Order(
                order_number="ORD20240319001",
                user_id=1,
                status="delivered",
                shipping_status="delivered",
                tracking_number="SF1234567890",
                shipping_address="北京市朝阳区xx路xx号",
                total_amount=428.0,
                created_at=now - timedelta(days=10),
                shipped_at=now - timedelta(days=8),
                delivered_at=now - timedelta(days=5)
            ),
            Order(
                order_number="ORD20240320002",
                user_id=1,
                status="shipped",
                shipping_status="in_transit",
                tracking_number="YT9876543210",
                shipping_address="北京市朝阳区xx路xx号",
                total_amount=5999.0,
                created_at=now - timedelta(days=3),
                shipped_at=now - timedelta(days=2),
            ),
            # 李四的订单
            Order(
                order_number="ORD20240321003",
                user_id=2,
                status="shipped",
                shipping_status="in_transit",
                tracking_number="JD1234567890",
                shipping_address="上海市浦东新区xx路xx号",
                total_amount=698.0,
                created_at=now - timedelta(days=2),
                shipped_at=now - timedelta(days=1),
            ),
            Order(
                order_number="ORD20240322004",
                user_id=2,
                status="paid",
                shipping_status="pending",
                shipping_address="上海市浦东新区xx路xx号",
                total_amount=2398.0,
                created_at=now - timedelta(days=1),
            ),
            # 王五的订单
            Order(
                order_number="ORD20240323005",
                user_id=3,
                status="pending",
                shipping_status="pending",
                shipping_address="广州市天河区xx路xx号",
                total_amount=118.0,
                created_at=now - timedelta(hours=12),
            ),
        ]
        db.add_all(orders)
        db.commit()
        print(f"创建了 {len(orders)} 个订单")

        # 创建订单商品
        order_items = [
            # ORD20240319001 的商品
            OrderItem(order_id=1, product_id=1, quantity=1, unit_price=299.0, subtotal=299.0),
            OrderItem(order_id=1, product_id=2, quantity=1, unit_price=129.0, subtotal=129.0),
            # ORD20240320002 的商品
            OrderItem(order_id=2, product_id=5, quantity=1, unit_price=5999.0, subtotal=5999.0),
            # ORD20240321003 的商品
            OrderItem(order_id=3, product_id=3, quantity=1, unit_price=1999.0, subtotal=1999.0),
            OrderItem(order_id=3, product_id=8, quantity=1, unit_price=29.0, subtotal=29.0),
            # ORD20240322004 的商品
            OrderItem(order_id=4, product_id=4, quantity=1, unit_price=599.0, subtotal=599.0),
            OrderItem(order_id=4, product_id=6, quantity=1, unit_price=399.0, subtotal=399.0),
            # ORD20240323005 的商品
            OrderItem(order_id=5, product_id=7, quantity=1, unit_price=89.0, subtotal=89.0),
            OrderItem(order_id=5, product_id=8, quantity=1, unit_price=29.0, subtotal=29.0),
        ]
        db.add_all(order_items)
        db.commit()
        print(f"创建了 {len(order_items)} 个订单商品")

        print("\n示例数据初始化完成！")
        print("=" * 50)
        print("测试账号（示例用户，密码均为 password123）：")
        print("  - 用户名: zhangsan, lisi, wangwu")
        print("=" * 50)
        print("\n订单数据：")
        print("  - 订单号: ORD20240319001, ORD20240320002, ORD20240321003, ORD20240322004, ORD20240323005")
        print("  - 快递单号: SF1234567890, YT9876543210, JD1234567890")
        print("\n产品数据：")
        print("  - 机械键盘、无线鼠标、显示器、耳机、笔记本电脑等")

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_sample_data()
