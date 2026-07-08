import os
from app.core.config import settings

print("=== Settings Values ===")
print(f"SAP_HOST: {settings.SAP_HOST}")
print(f"SAP_SYS_NR: {settings.SAP_SYS_NR}")
print(f"CLIENT: {settings.CLIENT}")
print(f"USER: {settings.USER}")
print(f"PASSWORD: {'*' * len(settings.PASSWORD) if settings.PASSWORD else 'EMPTY'}")
print(f"LANG: {settings.SAP_LANG}")
print("=======================")

print("\n=== conn_config ===")
for k, v in settings.conn_config.items():
    if k == 'passwd':
        print(f"{k}: {'*' * len(v) if v else 'EMPTY'}")
    else:
        print(f"{k}: {v}")
print("====================")

# 测试连接
try:
    import pyrfc
    print("\n🔗 Testing SAP connection...")
    conn = pyrfc.Connection(**settings.conn_config)
    print("✅ Connection successful!")
    attrs = conn.get_connection_attributes()
    print(f"📊 Connected: {attrs}")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")