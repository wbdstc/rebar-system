"""
数据库初始化脚本
用于创建 rebar_system 数据库和所有数据表

使用方式: python init_db.py
"""

import os
import sys
from datetime import datetime

# MySQL 连接配置
DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'port': int(os.environ.get('MYSQL_PORT', 3306)),
    'user': os.environ.get('MYSQL_USER', 'root'),
    'password': os.environ.get('MYSQL_PASSWORD', 'root'),  # 请修改为你的密码
    'database': 'rebar_system'
}


def create_database():
    """创建数据库（如果不存在）"""
    import pymysql
    
    print("=" * 50)
    print("钢筋工程智能管控平台 - 数据库初始化脚本")
    print("=" * 50)
    
    # 连接 MySQL（不指定数据库）
    print(f"\n[1/3] 连接 MySQL 服务器 ({DB_CONFIG['host']}:{DB_CONFIG['port']})...")
    
    try:
        conn = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset='utf8mb4'
        )
        print("      ✅ 连接成功")
    except Exception as e:
        print(f"      ❌ 连接失败: {e}")
        print("\n请检查:")
        print("  1. MySQL 服务是否已启动")
        print("  2. 用户名和密码是否正确")
        print("  3. 可通过环境变量设置: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD")
        sys.exit(1)
    
    # 创建数据库
    print(f"\n[2/3] 检查/创建数据库 '{DB_CONFIG['database']}'...")
    
    try:
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_CONFIG['database']}` "
                      f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        print(f"      ✅ 数据库 '{DB_CONFIG['database']}' 已就绪")
    except Exception as e:
        print(f"      ❌ 创建数据库失败: {e}")
        sys.exit(1)
    finally:
        conn.close()


def create_tables():
    """使用 SQLAlchemy 创建数据表"""
    print(f"\n[3/3] 创建数据表...")
    
    # 延迟导入，确保数据库已创建
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    
    # 创建临时 Flask 应用
    app = Flask(__name__)
    
    # 配置数据库连接
    db_uri = (f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
              f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
              f"?charset=utf8mb4")
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'pool_recycle': 3600,
        'pool_pre_ping': True
    }
    
    db = SQLAlchemy(app)
    
    # ========================================
    # 定义数据模型
    # ========================================
    
    class InspectionRecord(db.Model):
        """检测记录表"""
        __tablename__ = 'inspection_records'
        
        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        
        # 基本信息
        record_id = db.Column(db.String(50), unique=True, nullable=False, comment='记录编号')
        inspection_type = db.Column(db.String(20), nullable=False, comment='检测类型: spacing/counting/column')
        project_name = db.Column(db.String(100), comment='项目名称')
        location = db.Column(db.String(200), comment='检测位置')
        
        # 柱截面信息（针对 column 模式）
        column_id = db.Column(db.String(20), comment='柱号')
        section_width = db.Column(db.Integer, comment='截面宽度 mm')
        section_height = db.Column(db.Integer, comment='截面高度 mm')
        
        # 检测结果
        detected_count = db.Column(db.Integer, comment='检测数量')
        design_total = db.Column(db.Integer, comment='设计数量')
        compliance_status = db.Column(db.String(20), comment='合规状态: PASS/FAIL/WARNING')
        compliance_message = db.Column(db.Text, comment='合规性说明')
        
        # 配筋信息 (JSON 格式存储)
        rebar_config = db.Column(db.JSON, comment='配筋配置')
        
        # 检测数据 (JSON 格式存储)
        predictions = db.Column(db.JSON, comment='AI 检测结果')
        hoop_path = db.Column(db.JSON, comment='箍筋路径')
        
        # 图片存储
        image_url = db.Column(db.String(500), comment='原始图片 URL (MinIO)')
        result_image_url = db.Column(db.String(500), comment='结果图片 URL (MinIO)')
        
        # 操作信息
        inspector = db.Column(db.String(50), comment='检测人员')
        created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
        updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
        
        def to_dict(self):
            return {
                'id': self.id,
                'record_id': self.record_id,
                'inspection_type': self.inspection_type,
                'project_name': self.project_name,
                'location': self.location,
                'column_id': self.column_id,
                'section_size': [self.section_width, self.section_height] if self.section_width else None,
                'detected_count': self.detected_count,
                'design_total': self.design_total,
                'compliance_status': self.compliance_status,
                'compliance_message': self.compliance_message,
                'rebar_config': self.rebar_config,
                'image_url': self.image_url,
                'inspector': self.inspector,
                'created_at': self.created_at.isoformat() if self.created_at else None,
            }
    
    class User(db.Model):
        """用户表"""
        __tablename__ = 'users'
        
        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        username = db.Column(db.String(50), unique=True, nullable=False, comment='用户名')
        password_hash = db.Column(db.String(255), nullable=False, comment='密码哈希')
        real_name = db.Column(db.String(50), comment='真实姓名')
        role = db.Column(db.String(20), default='inspector', comment='角色: admin/inspector/viewer')
        department = db.Column(db.String(100), comment='部门')
        phone = db.Column(db.String(20), comment='手机号')
        email = db.Column(db.String(100), comment='邮箱')
        is_active = db.Column(db.Boolean, default=True, comment='是否启用')
        created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
        last_login = db.Column(db.DateTime, comment='最后登录时间')
    
    class Project(db.Model):
        """项目表"""
        __tablename__ = 'projects'
        
        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        project_code = db.Column(db.String(50), unique=True, nullable=False, comment='项目编号')
        project_name = db.Column(db.String(200), nullable=False, comment='项目名称')
        location = db.Column(db.String(300), comment='项目地址')
        contractor = db.Column(db.String(100), comment='承建单位')
        supervisor = db.Column(db.String(100), comment='监理单位')
        start_date = db.Column(db.Date, comment='开工日期')
        end_date = db.Column(db.Date, comment='竣工日期')
        status = db.Column(db.String(20), default='active', comment='状态: active/completed/paused')
        created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    
    class SystemLog(db.Model):
        """系统日志表"""
        __tablename__ = 'system_logs'
        
        id = db.Column(db.Integer, primary_key=True, autoincrement=True)
        log_type = db.Column(db.String(20), comment='日志类型: info/warning/error')
        module = db.Column(db.String(50), comment='模块')
        action = db.Column(db.String(100), comment='操作')
        message = db.Column(db.Text, comment='日志内容')
        user_id = db.Column(db.Integer, comment='操作用户 ID')
        ip_address = db.Column(db.String(50), comment='IP 地址')
        created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    
    # 创建所有表
    with app.app_context():
        try:
            db.create_all()
            print("      ✅ 所有数据表创建成功!")
            print("\n已创建的表:")
            print("      - inspection_records (检测记录表)")
            print("      - users (用户表)")
            print("      - projects (项目表)")
            print("      - system_logs (系统日志表)")
        except Exception as e:
            print(f"      ❌ 创建表失败: {e}")
            sys.exit(1)


def main():
    """主函数"""
    create_database()
    create_tables()
    
    print("\n" + "=" * 50)
    print("🎉 数据库初始化完成!")
    print("=" * 50)
    print(f"\n数据库连接信息:")
    print(f"  Host: {DB_CONFIG['host']}")
    print(f"  Port: {DB_CONFIG['port']}")
    print(f"  Database: {DB_CONFIG['database']}")
    print(f"  User: {DB_CONFIG['user']}")
    print("\n下一步:")
    print("  1. 启动后端: python app.py")
    print("  2. 初始化前端: cd frontend && npm install && npm run dev")


if __name__ == '__main__':
    main()
