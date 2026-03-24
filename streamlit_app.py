"""Streamlit聊天界面 - 调用后端API"""
import streamlit as st
import requests
import json
from datetime import datetime

# 配置
API_BASE_URL = "http://localhost:8000"

# 页面配置
st.set_page_config(
    page_title="电商客服",
    page_icon="💬",
    layout="centered"
)


def init_session_state():
    """初始化会话状态"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "user_id" not in st.session_state:
        st.session_state.user_id = None
    if "username" not in st.session_state:
        st.session_state.username = None
    if "token" not in st.session_state:
        st.session_state.token = None


def login(username: str, password: str) -> dict:
    """登录"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            return {"error": "用户名或密码错误"}
        else:
            return {"error": f"登录失败: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "无法连接到后端服务，请确保FastAPI服务已启动"}
    except Exception as e:
        return {"error": str(e)}


def register(username: str, password: str, email: str = "") -> dict:
    """注册"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/auth/register",
            json={"username": username, "password": password, "email": email},
            timeout=10
        )
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 400:
            return {"error": "用户名已存在"}
        else:
            return {"error": f"注册失败: {response.status_code}"}
    except requests.exceptions.ConnectionError:
        return {"error": "无法连接到后端服务"}
    except Exception as e:
        return {"error": str(e)}


def chat_auto(message: str, history: list, user_id: int = None) -> dict:
    """调用智能聊天接口"""
    try:
        payload = {
            "messages": history + [{"role": "user", "content": message}],
            "temperature": 0.7
        }
        if user_id:
            payload["user_id"] = user_id

        response = requests.post(
            f"{API_BASE_URL}/api/chat/auto",
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"content": f"请求失败: {response.status_code}", "error": response.text}
    except requests.exceptions.Timeout:
        return {"content": "请求超时，请稍后重试"}
    except requests.exceptions.ConnectionError:
        return {"content": "无法连接到后端服务"}
    except Exception as e:
        return {"content": f"错误: {str(e)}"}


def chat_order(message: str, history: list, user_id: int = None) -> dict:
    """调用订单查询聊天接口"""
    try:
        payload = {
            "messages": history + [{"role": "user", "content": message}],
            "temperature": 0.7
        }
        if user_id:
            payload["user_id"] = user_id

        response = requests.post(
            f"{API_BASE_URL}/api/chat/order",
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"content": f"请求失败: {response.status_code}"}
    except Exception as e:
        return {"content": f"错误: {str(e)}"}


def chat_product(message: str, history: list) -> dict:
    """调用产品推荐聊天接口"""
    try:
        payload = {
            "messages": history + [{"role": "user", "content": message}],
            "temperature": 0.7
        }

        response = requests.post(
            f"{API_BASE_URL}/api/chat/product",
            json=payload,
            timeout=60
        )
        if response.status_code == 200:
            return response.json()
        else:
            return {"content": f"请求失败: {response.status_code}"}
    except Exception as e:
        return {"content": f"错误: {str(e)}"}


def health_check() -> dict:
    """健康检查"""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return response.json() if response.status_code == 200 else {"status": "unhealthy"}
    except:
        return {"status": "unhealthy"}


def render_auth_sidebar():
    """渲染侧边栏登录/注册表单"""
    with st.sidebar:
        st.title("用户认证")

        if st.session_state.token:
            st.success(f"已登录: {st.session_state.username}")
            if st.button("退出登录"):
                st.session_state.token = None
                st.session_state.username = None
                st.session_state.user_id = None
                st.rerun()
        else:
            tab1, tab2 = st.tabs(["登录", "注册"])

            with tab1:
                login_user = st.text_input("用户名", key="login_user")
                login_pass = st.text_input("密码", type="password", key="login_pass")
                if st.button("登录", use_container_width=True):
                    if login_user and login_pass:
                        with st.spinner("登录中..."):
                            result = login(login_user, login_pass)
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                st.session_state.token = result["access_token"]
                                st.session_state.user_id = result["user_id"]
                                st.session_state.username = result["username"]
                                st.success("登录成功!")
                                st.rerun()
                    else:
                        st.warning("请输入用户名和密码")

            with tab2:
                reg_user = st.text_input("用户名", key="reg_user")
                reg_pass = st.text_input("密码", type="password", key="reg_pass")
                reg_email = st.text_input("邮箱(可选)", key="reg_email")
                if st.button("注册", use_container_width=True):
                    if reg_user and reg_pass:
                        with st.spinner("注册中..."):
                            result = register(reg_user, reg_pass, reg_email)
                            if "error" in result:
                                st.error(result["error"])
                            else:
                                st.session_state.token = result["access_token"]
                                st.session_state.user_id = result["user_id"]
                                st.session_state.username = result["username"]
                                st.success("注册成功并已登录!")
                                st.rerun()
                    else:
                        st.warning("请输入用户名和密码")

        # 健康检查
        st.divider()
        st.caption("系统状态")
        health = health_check()
        if health.get("status") == "healthy":
            st.success("后端服务正常")
        else:
            st.error("后端服务不可用")


def render_chat_page():
    """渲染聊天页面"""
    st.title("💬 电商客服")

    # 模式选择
    col1, col2, col3 = st.columns(3)
    with col1:
        st.success("🔍 智能模式 - 自动识别意图")
    with col2:
        st.info("📦 订单查询 - 查询订单物流")
    with col3:
        st.info("🛍️ 产品推荐 - 获取产品推荐")

    st.divider()

    # 显示历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
            if "intent" in msg and msg["intent"]:
                st.caption(f"意图: {msg['intent']}")

    # 用户输入
    if prompt := st.chat_input("输入您的问题..."):
        # 添加用户消息
        st.session_state.messages.append({
            "role": "user",
            "content": prompt
        })
        with st.chat_message("user"):
            st.write(prompt)

        # 调用API
        with st.spinner("思考中..."):
            # 构建历史消息（不含当前消息）
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
                if m["role"] in ["user", "assistant"]
            ]

            result = chat_auto(prompt, history, st.session_state.user_id)

        # 显示助手回复
        with st.chat_message("assistant"):
            st.write(result.get("content", "抱歉，发生了错误"))

            # 显示意图信息
            if result.get("intent"):
                st.caption(f"识别意图: {result['intent']}")
            if result.get("tool_used"):
                st.caption(f"使用工具: {result.get('tool_name', '未知')}")

        # 保存到历史
        st.session_state.messages.append({
            "role": "assistant",
            "content": result.get("content", "发生了错误"),
            "intent": result.get("intent")
        })

    # 清空对话按钮
    if st.session_state.messages and st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()


def main():
    init_session_state()
    render_auth_sidebar()
    render_chat_page()


if __name__ == "__main__":
    main()
