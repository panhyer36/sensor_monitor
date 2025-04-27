# AMI 系统（UWM Capstone 项目）

空气监测接口系统是一个由 UWM Capstone 项目团队使用的传感器数据监测平台。它是一个基于 Django 的 Web 应用程序，用于接收、存储、可视化和导出各种环境传感器的数据。

## 主要功能

*   **数据接收**：提供 API 端点以接收来自传感器的数据（温度、湿度、CO2、PM1.0、PM2.5、PM10.0）。
*   **数据查询**：提供 RESTful API 以查询存储的传感器数据（需要用户登录），支持按时间范围过滤。
*   **数据导出**：允许登录用户导出指定时间范围和传感器类型的 CSV 或 JSON 文件。
*   **用户认证**：包括用户注册、登录和注销功能。
*   **Gmail 通知**：当数据超过阈值时发送通知。
*   **数据可视化**：提供图表或其他形式来显示传感器数据趋势。
*   **聊天机器人**：集成多个聊天机器人，提供免费或付费功能。

## 技术栈

*   **后端**：Python、Django、Django REST Framework
*   **数据库**：SQLite
*   **前端**：HTML、CSS、JavaScript
*   **AI 功能**：MCP（模型上下文协议技术，用于 DeepSeek AI）、混合策略应答技术（用于基础 AI）

## 安装与运行

1.  **克隆仓库**：
    ```bash
    git clone https://github.com/panhyer36/sensor_monitor.git
    cd sensor_monitor
    ```

2.  **创建并激活虚拟环境**：
    ```bash
    python -m venv venv
    source venv/bin/activate  # 在 Windows 上使用 `venv\Scripts\activate`
    ```

3.  **安装依赖**：
    ```bash
    pip install -r requirements.txt
    ```

4.  **数据库迁移**：
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **创建管理员用户**：
    您可以使用提供的脚本：
    ```bash
    python create_admin.py
    ```
    或者使用 Django 命令：
    ```bash
    python manage.py createsuperuser
    ```

6.  **配置 Google Mail API 密钥**
    （您需要在 `.env` 中设置 API 凭据）
    ```
    EMAIL_HOST_USER=your_email@gmail.com
    EMAIL_HOST_PASSWORD=your_app_password
    ```

7.  **运行开发服务器**：
    您需要运行两个进程，最好在不同的终端中：
    ```bash
    # 终端 1：运行 Django 开发服务器
    python manage.py runserver
    ```
    ```bash
    # 终端 2：运行 MCP 服务器
    mcpo --host 127.0.0.1 --port 8002 -- python MCP_server/mcp_server.py
    ```

## 团队
*   该项目由威斯康星大学密尔沃基分校的一个团队用于 Capstone 项目。
*   AMI 团队
    *   成员 1：YU-ERH, PAN
    *   成员 2：Yen-Lin, Chang
    *   成员 3：Carson K Lisowe
    *   成员 4：Taiwo Boluwaji Abe
    *   成员 5：Collin Brey
    *   成员 6：Matthew Scott Maijala

## 致谢
特别感谢以下开源项目：
*   MCPO：https://github.com/open-webui/mcpo
*   MCP：https://github.com/modelcontextprotocol
*   Comitup：https://github.com/davesteele/comitup (与本项目没有直接关系，用于树莓派上发送传感器数据的网络连接过程，并作为核心组件安装。我们未修改或披露其任何代码。由于其 GPL-2.0 许可证，我们特此声明并表示感谢。) 