# Facebook Tool

## Thư mục

| Vị trí | Nội dung |
| --- | --- |
| `source/` | Mã nguồn chạy tool, các module, tài nguyên và test |
| `source/client_app.py` | File chính của ứng dụng |
| `source/facebook/` | Module Facebook |
| `source/license_worker/` | Máy chủ quản lý bản quyền |
| `source/tests/` | Kiểm thử tự động |
| `dist/client_app.exe` | Bản EXE để sử dụng/gửi khách hàng |
| `build/` | File tạm khi đóng gói |
| `docs/` | Tài liệu giải thích luồng chạy |
| `archive/` | File sao lưu cũ, không được dùng để build |

Các thư mục `build_rebuild` và `dist_rebuild` được giữ nguyên vì là output cũ.

## Chạy và đóng gói

Chạy các lệnh dưới đây tại `E:\FacebookTool_Project`:

```powershell
pip install -r requirements-build.txt
python source/client_app.py
python -m pytest -q
pyinstaller client_app.spec
```

`release.ps1`, `client_app.spec`, `requirements*.txt`, `pytest.ini` và `version.json`
được giữ ở thư mục gốc để build/phát hành như trước. Không sửa `version.json` chỉ
vì di chuyển mã nguồn.

Lệnh phát hành vẫn là `./release.ps1 <phiên bản> "Nội dung cập nhật"`.
Hướng dẫn môi trường build chi tiết: [BUILD.md](BUILD.md).

Dữ liệu tài khoản, lịch sử và bản quyền vẫn ở `%LOCALAPPDATA%\FacebookAutoTool`,
không bị di chuyển hoặc xóa trong lần sắp xếp này.
