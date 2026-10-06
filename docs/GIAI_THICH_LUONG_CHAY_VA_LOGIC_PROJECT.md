# Giải thích luồng chạy và logic hiện tại của Facebook Workspace Pro

**Ngày đối chiếu:** 03/10/2026. **Project:** `E:\FacebookTool_Project`. **Phiên bản trong source:** `2.3.0`.

**Commit gốc:** `7b4e0aca56acc83f9f5341d3bf715e8fb0697123`.

Tài liệu này mô tả code đang có, không phải đề xuất thiết kế và không khẳng định mọi chức năng đã ổn định ngoài thực tế. Việc tạo tài liệu không sửa production code, không chạy Facebook, không build, không cập nhật ứng dụng và không phát hành.

## Cách đọc

- Mục 1-5: cấu trúc project, dữ liệu và cách bắt đầu chạy.
- Mục 6-11: đăng nhập, proxy, Create Page, kết bạn, Page/admin và các tác vụ khác.
- Mục 12-16: lịch sử, dừng chạy, cập nhật, release và server cấp phép.
- Mục 17-19: test, giới hạn thực tế và thuật ngữ.
- Phụ lục: tra cứu từng class/hàm, kể cả callback bên trong hàm và hàm mô phỏng của test, bằng liên kết đến dòng source.

**Phạm vi “tất cả code”:** giải thích theo khối trách nhiệm và từng hàm, không diễn giải lại từng dòng trống, từng import hay từng dòng bố trí widget. Các hằng số, cấu hình, script và file dữ liệu được giải thích theo nhóm. Không giải mã EXE, không mô tả internals của thư viện bên thứ ba và không đưa mật khẩu/cookie/token/license thật vào tài liệu.

## 1. Bản đồ project

| File/nhóm | Vai trò thực tế |
|---|---|
| `client_app.py` | Ứng dụng Tkinter; account parser; quản lý state, proxy, Playwright; các tác vụ Facebook; cập nhật EXE; kiểm tra license. |
| `account_history.py` | Lưu trạng thái/kết quả và sự kiện vào SQLite; loại dữ liệu đăng nhập khỏi lịch sử được lưu. |
| `release.ps1` | Kiểm tra môi trường, sửa version, test, build, hash, Git/GitHub Release và cập nhật metadata. Chỉ chạy khi người dùng gọi script. |
| `version.json` | Metadata update: `version`, `download_url`, `sha256`, `changelog`, `mandatory`. Không điều khiển Facebook automation. |
| `client_app.spec` | Cấu hình PyInstaller đang có trên máy: EXE tên `client_app`, không console, kèm assets/icon. File này đang bị `.gitignore` loại khỏi Git. |
| `requirements.txt` | Dependencies chạy: cryptography 49.0.0, Playwright 1.60.0, openpyxl 3.1.5. |
| `requirements-build.txt` | Nạp requirements chạy và PyInstaller 6.22.2. Pytest được release sử dụng nhưng không nằm trong hai file requirements này. |
| `admin_key_gen.py` | Hiện chỉ in hướng dẫn tạo/quản lý key bằng Telegram; không còn là chương trình tự sinh key offline. |
| `license_worker/src/index.js` | Cloudflare Worker: API kiểm tra license và webhook bot Telegram quản trị license. |
| `license_worker/schema.sql` | Schema D1 của bảng license và chỉ mục HWID. |
| `license_worker/wrangler.toml` | Tên Worker, entrypoint, ngày compatibility, binding D1 và cấu hình admin. Secret bot/webhook được nạp riêng. |
| `license_worker/README.md` | Hướng dẫn dựng server license, tạo DB, nạp secret, deploy và cấu hình webhook. Không được app tự thực thi. |
| `tests/test_core.py` | Test logic lõi, cập nhật, account, Page, checkpoint, lifecycle và nhiều nhánh UI bằng mô phỏng. |
| `tests/test_targeted_runtime.py` | Regression tests tập trung vào runtime mô phỏng, selector, proxy, isolation và lịch sử. |
| `tests/runtime_restart_probe.py` | Chương trình probe riêng để kiểm tra restart PyInstaller; không phải test tự động của pytest thông thường. |
| `assets/`, `picture.ico` | Logo, ảnh kích thước nhỏ và icon cửa sổ/EXE. Không thực hiện automation. |
| `.gitignore` | Loại build/dist, spec, settings/license, private key, cache Python và dữ liệu công cụ khỏi Git. |
| File tên bắt đầu `e.ps1 2.1.6 ...` | Nội dung hiện là output/diff đã lưu, không phải script release chuẩn. Không có luồng app sử dụng file này được xác định trong source. |

`dist/`, `build/`, cache và EXE là sản phẩm tạo ra, không phải nguồn logic. Có EXE trên máy không chứng minh nó được build từ đúng source đang mô tả.

## 2. Sơ đồ tổng thể

```text
python client_app.py / client_app.exe
  -> nạp module, tạo thư mục dữ liệu, cấu hình asyncio Windows
  -> main()
     -> đọc license -> xác thực online
     -> thiếu/không hợp lệ: cửa sổ kích hoạt -> xác thực -> lưu license
     -> MainToolApp + vòng lặp Tkinter
        -> dựng UI, load settings, lịch sử, đồng hồ
        -> một thread kiểm tra phiên bản
        -> người dùng nhập account/proxy/target, chọn chế độ
        -> BẮT ĐẦU: chụp cấu hình -> tạo thread chạy
           -> asyncio.run(main_worker())
           -> pre-flight -> account jobs -> chia batch
           -> từng batch tuần tự
              -> các account chạy đồng thời dưới semaphore
                 -> ContextVar của account
                 -> proxy -> browser/context/page riêng
                 -> cookie -> verify -> fallback login nếu cần
                 -> tương tác tùy chọn -> các module được chọn
                 -> kết quả/log riêng -> đóng tài nguyên
           -> tổng kết -> dọn account đầu vào đã xử lý -> Telegram
        -> UI nhận callback qua queue/post_ui
        -> finish_run khôi phục nút khi thread thực sự kết thúc
```

Có ba hệ thống riêng: desktop automation, server license và script release. Server license không tạo Page; script release không chạy account.

## 3. Khởi tạo, dữ liệu cục bộ và license

### 3.1. Khi import module

Các import phục vụ UI (`tkinter`/`ttk`), đa luồng/async (`threading`, `asyncio`, `queue`, `ContextVar`), Playwright, HTTP, crypto, CSV/JSON, đường dẫn và Windows registry. Module cấu hình event loop phù hợp Windows nếu cần và tạo thư mục dữ liệu.

`output_path()` đưa file kết quả về `%LOCALAPPDATA%\FacebookAutoTool`; nếu thiếu LOCALAPPDATA thì dùng thư mục tương ứng dưới home. `resource_path()` lấy assets cạnh source hoặc từ thư mục giải nén `sys._MEIPASS` khi đóng gói PyInstaller.

Các nhóm hằng số gồm version/endpoint, trạng thái, selector, tên/từ khóa mẫu, alias danh mục, schema file và theme. Đây là dữ liệu hỗ trợ, không phải mọi selector đều độc lập ngôn ngữ.

### 3.2. License

`main()` đọc `license.lic`; `verify_license()` gửi key/HWID đến `/validate` với timeout. Hợp lệ thì mở app, không hợp lệ thì mở `LicenseCheckDialog`. Kích hoạt thành công lưu key cục bộ và mở giao diện chính.

`get_hwid()` tổng hợp thông tin Windows như MachineGuid, serial ổ C và UUID hệ thống, băm để tạo mã máy. Có nhánh fallback khi không đọc được các nguồn này; không nên hiểu HWID luôn bất biến trong mọi trường hợp.

Kiểm tra license được gọi lúc khởi động/kích hoạt. Không có vòng kiểm tra thu hồi license định kỳ trong toàn bộ thời gian batch đang chạy được xác định ở luồng này.

### 3.3. Settings

`save_settings()` ghi các tùy chọn UI. Accounts, proxies và Telegram token được mã hóa bằng Fernet với khóa dẫn xuất từ HWID và salt của chương trình; một số cấu hình/target khác được lưu dạng thường. `load_settings()` nạp lại và có tương thích dữ liệu cũ qua `unprotect_setting()`.

Mã hóa settings không đồng nghĩa mọi file output đều được mã hóa. `license.lic`, raw exports, checkpoint list và một số file module khác vẫn là dữ liệu đọc được.

## 4. Nhập và parse account: hành vi đang có

Nguồn đối chiếu: [parse_any_account_line](E:/FacebookTool_Project/client_app.py:1876).

### 4.1. Raw line và fields

1. `raw_line` được giữ, trừ ký tự xuống dòng cuối.
2. `source_line` bỏ STT kiểu `1.`, `1-` hoặc prefix số/khoảng trắng rồi trim.
3. `fields` là kết quả `split('|')`; các cột rỗng vẫn tồn tại, nhưng nội dung từng cột bị `strip()`.
4. Parser quét nội dung để đoán UID/password/2FA/cookie/token/email/proxy.
5. Không tìm cookie thì trả `None`. Tìm cookie nhưng thiếu password vẫn có thể trả account.
6. Không có UID thì thử `c_user`; cuối cùng có thể dùng nhãn `UID_<STT>`.

**Quan trọng:** parser hiện tại KHÔNG ép contract duy nhất `UID|PASSWORD|2FA|COOKIE|TOKEN` theo vị trí. Không nên dựa vào tài liệu cũ để kết luận parser đã chuyển hoàn toàn sang contract đó.

| Dữ liệu | Cách nhận diện hiện tại |
|---|---|
| Cookie | Field chuẩn hóa được bởi `normalize_cookie_input()`. |
| Token | Prefix `EAAB`/`EAAA`, hoặc heuristic field dài có dấu chấm và không có `@`. |
| Email | Có `@` và dấu chấm. |
| Proxy | `parse_proxy()` nhận diện được. |
| 2FA | Chuỗi alphanumeric dài 16 hoặc 32, không toàn số. |
| UID | Chuỗi số dài từ 5; nếu thiếu thì dùng cookie hoặc nhãn fallback. |
| Password | Field chưa phân loại sau khi UID đã có. |

Parser còn xử lý prefix `FACEBOOK`, `COOKIE`, `TOKEN` và các dòng có cookie theo dạng mà helper nhận diện. RAW UID/password không có cookie không đủ điều kiện của parser hiện tại. Format có cột rỗng như `UID|PASSWORD|2FA|||COOKIE|TOKEN` vẫn có thể được quét, không bị bắt buộc đúng năm cột.

Hệ quả: password 16/32 ký tự phù hợp heuristic có thể bị nhận nhầm là 2FA. `fields` vẫn lưu nội dung nhưng mapping sang password/2FA có thể sai. `unknown_fields` hiện được trả là danh sách rỗng; không phải bộ phân loại đầy đủ của mọi trường chưa dùng.

### 4.2. State sau parse

Account gồm `type`, `raw_line`, `source_line`, `fields`, `unknown_fields`, `uid`, `name`, `pwd`/`password`, `2fa`, `cookie`, `token`, `email`, `proxy`, `data`, `locale`, `country`, `timezone`.

`data` hiện thường là cookie vì type trả về là `COOKIE`. Nó không phải bản sao đầy đủ thay thế raw line.

`serialize_account_line()` trả raw line; `serialize_account_lines()` nối chúng bằng xuống dòng. `auto_format_cookie_numbers()` làm mới số đếm/bảng, không rewrite raw input thành cookie-only.

Tuy nhiên các thao tác import từ file, thêm/xóa và loại account đã xử lý vẫn có thể dựng lại textbox với STT và trim dòng. Phải phân biệt “parse/serialize giữ raw” với “mọi thao tác UI giữ byte-for-byte” vì hai điều này hiện không tương đương.

### 4.3. Locale/country

Có helper `normalize_account_locale()`, `normalize_account_timezone()`, `split_account_metadata()` và `browser_locale_options()`. Nhưng parser hiện trả `locale=AUTO`, `country=''`, `timezone=''`, không gọi helper tách metadata trong nhánh này. Vì vậy không thể khẳng định chỉ thêm locale vào raw input là worker tự sử dụng đúng locale.

`AUTO` không suy luận ngôn ngữ từ quốc gia/IP. Nếu state/config có locale/timezone hợp lệ, browser nhận các giá trị đó; proxy country không quyết định selector.

## 5. UI, snapshot cấu hình, thread và batch

### 5.1. Giao diện

`MainToolApp.__init__()` tạo state/history store, lock, queue, flags và cửa sổ; dựng hai tab chính: Trang chủ và Thống kê & quản lý. Có bốn theme, đồng hồ, nhập file, danh sách account/proxy, chọn mode, nhật ký, bảng trạng thái, tham số và nút chạy/dừng.

Bảng quản lý chứa chọn dòng, STT, UID, Password, 2FA, Status, Action. Cookie/token không có cột riêng trên bảng này. Copy dữ liệu gốc hoặc xuất raw line vẫn có thể chứa toàn bộ bí mật.

Bảng trạng thái hiển thị account, status, kết quả tác vụ, Page tiếp/còn lại và tác vụ hiện tại. Chọn account chuyển nhật ký sang log của account đó; nút log tổng chuyển về thông báo toàn đợt.

### 5.2. Cấu hình được chụp lúc chạy

`capture_run_config()` đọc widget một lần trên UI thread: raw accounts, proxies, targets, STT/checkbox chọn, parsed states, resolved proxies, threads/batch, proxy mode/API, headless, chỉ tiêu, delay, Telegram, kích thước màn hình, modes và options.

| Tham số | Fallback khi đọc cấu hình | Giới hạn |
|---|---:|---|
| Threads | 6 | 1-20 |
| Batch size | 5 | 1-10000 |
| Số account/proxy khi chia nhóm | 20 | 1-10000 |
| Số bạn/account | 25 | 1-10000 |
| Số Page/account | 5 | 1-100 |
| Max Create Page workers | 3 | 1-10 |
| Delay click | 25-35 giây | 0-86400 mỗi đầu khoảng |
| Delay Page | 60-120 giây | 0-86400 mỗi đầu khoảng |
| Lướt Feed trước tác vụ | 10 phút | 0-1440 |
| Xem review | 5 phút | 0-1440 |

Các số này không phải luôn là giá trị bạn đang thấy: settings đã lưu có thể thay thế. Min/max bị đảo sẽ được sắp xếp lại.

Khi nhập trên 20 threads app giới hạn; khi yêu cầu trên 12 và chưa headless, app tự bật chạy ẩn. Nếu bật Create Page/admin, `effective_account_worker_count()` còn giới hạn worker theo tham số riêng. Giới hạn này áp dụng cho account worker, không phải một pool Page độc lập bên trong.

### 5.3. Luồng chạy

`start_thread()` lưu settings, chụp cấu hình, khóa Bắt đầu, mở Dừng và tạo daemon thread. Thread gọi `run_process()`, bên trong `asyncio.run(main_worker())`.

`main_worker()` lọc dòng trống/comment, parse STT dạng `1,3,5-9`, tạo kế hoạch Page nếu cần, dựng job/account, chia batch và mở Playwright. Batch chạy lần lượt; trong batch, tasks async chạy dưới semaphore. `gather(return_exceptions=True)` gom kết quả thay vì để một account lỗi luôn đánh sập mọi account khác.

Ví dụ 20 account, batch size 5: bốn batch. Nếu semaphore cho ba account, mỗi batch vẫn chỉ tối đa ba account thực sự xử lý cùng lúc.

**Giới hạn hiện tại:** `start_thread()` đặt `is_running=True` trước khi gọi `reload_table_from_text()`, trong khi reload bỏ qua khi đang chạy. Bảng/state cũ có thể bị đưa vào snapshot dù textbox đã đổi. Đây là hành vi cần sửa riêng, không được tài liệu này khắc phục.

### 5.4. UI thread

Worker gửi `post_ui(callback)` vào queue. `_drain_ui_queue()` được Tk gọi khoảng 50 ms để thực hiện callback. AccountStateStore dùng RLock cho state; mỗi async account dùng ContextVar riêng để route log đúng account.

Không có 50-100 browser đồng thời trong giới hạn hiện tại. Số account đầu vào có thể nhiều hơn số worker vì sẽ được xếp hàng/batch.

## 6. Proxy, browser context và vòng đời phiên

### 6.1. Chọn proxy

Các chế độ UI: luân phiên, theo nhóm, ngẫu nhiên, riêng/account và API xoay. Proxy đã preview/resolve được giữ trong snapshot/cache để không random lại giữa chừng. Inline proxy thuộc account được ưu tiên theo nhánh chọn hiện tại.

- Luân phiên: theo chỉ số account modulo số proxy.
- Theo nhóm: nhiều account dùng một proxy theo ratio; thiếu proxy thì tái dùng proxy cuối theo logic hiện tại.
- Ngẫu nhiên: dùng lựa chọn đã cache theo danh sách/mode/account.
- Riêng/account: lấy proxy thuộc account.
- API: fetch qua thread phụ, serialize bằng async lock; lấy endpoint cho worker rồi dùng endpoint đó.

`parse_proxy()` hỗ trợ HTTP/HTTPS/SOCKS4/SOCKS5, host:port, host:port:user:password và URL có auth/IPv6. Port phải hợp lệ; auth bị thiếu một nửa bị loại theo validation.

Nếu proxy được yêu cầu nhưng không resolve/parse được, account bị ERROR, không tự fallback sang IP máy trong nhánh automation. Nếu cấu hình hoàn toàn không dùng proxy, direct connection vẫn được phép.

Tool không có SDK 9proxy riêng. Với phần mềm forward proxy trên máy, endpoint mà browser dùng phải là endpoint đang nghe, chẳng hạn `127.0.0.1:<port>` theo cấu hình của nhà cung cấp. IP exit hiện trong danh sách nhà cung cấp không tự chứng minh đó là host đang mở proxy cho tool.

Giữ cùng endpoint không đảm bảo exit IP không bị phần mềm/provider đổi bên ngoài. Code không xác nhận liên tục exit IP/country. Các request license/update/Telegram và một số tiện ích urllib không mặc nhiên dùng proxy của browser account.

### 6.2. Browser riêng cho account

`create_browser_page()` tìm Chrome/Edge cài sẵn hoặc dùng Chromium của Playwright, launch có proxy, tạo `new_context()` rồi page. Context automation là context riêng không persistent: cookie/storage không chủ ý chia sẻ với account khác.

Cấu hình locale/timezone chỉ được nạp khi dữ liệu hợp lệ. Có init script chỉnh một số thuộc tính trình duyệt. Việc này không chứng minh tránh được phát hiện automation; không có bảo đảm “không checkpoint”.

Browser mở endpoint Facebook `/robots.txt` để kiểm tra khả năng phản hồi. Response thiếu, 407 hoặc từ 500 bị xem lỗi; không phải mọi HTTP status đều được coi lỗi và đây chưa phải phép xác minh login.

Launch có retry hữu hạn. Context/page được trả về cho worker sau khi khởi tạo hoàn tất. Worker thường đóng page/context/browser trong `finally` với timeout từng tài nguyên.

**Ngoại lệ cần lưu ý:** cleanup trong nhánh lỗi của chính `create_browser_page()` chưa có timeout tương tự. Nếu bị cancel trước khi trả tài nguyên cho caller, nhánh `except Exception` không bắt được `CancelledError`. Vì vậy chưa thể cam kết mọi lỗi khởi tạo đều đóng sạch tiến trình.

### 6.3. Mở profile thủ công

`open_selected_profile()` là đường riêng: persistent profile dưới `browser_profiles/`, chạy thread riêng, giữ cửa sổ tới khi đóng rồi close context. Nó không phải context dùng cho mọi account batch. Đóng cửa sổ thủ công và bấm Dừng batch là hai tình huống khác nhau.

## 7. Đăng nhập và trạng thái account

### 7.1. Trình tự

`process_account_scoped()` đặt account ContextVar. `process_account()` lấy semaphore, đặt CHECKING, parse cookie/proxy, mở browser và khởi động watcher checkpoint.

Cookie được add vào context, mở Facebook và gọi `verify_facebook_session()`. Nếu cookie/session không hợp lệ, có UID/password thì thử `login_facebook_user_pass()`; có nhánh TOTP khi flow nhận diện 2FA tương ứng. Sau xác minh phù hợp mới đi tiếp các tác vụ.

Token hiện được parse/lưu và có tiện ích trích token, nhưng không phải mọi tác vụ dùng token làm phương thức đăng nhập; automation chính vẫn dùng browser/cookie và fallback password.

### 7.2. State đang hỗ trợ

| Account status | Nghĩa |
|---|---|
| UNKNOWN | Chưa có xác minh phiên đủ để kết luận. |
| CHECKING | Đang xử lý kiểm tra/đăng nhập. |
| LIVE | Worker đã chấp nhận phiên theo helper hiện tại; xem giới hạn bên dưới. |
| DIE | Nhánh account/cookie/login được phân loại không hợp lệ. |
| ERROR | Lỗi kỹ thuật/đầu vào/mạng/automation. |
| CHECKPOINT | Checkpoint được nhận diện; khóa các tác vụ tiếp của account này. |

Account status khác task result. Account LIVE vẫn có thể Create Page FAILED. Không được đọc LIVE thành “đã tạo Page thành công”.

### 7.3. Xác minh phiên hiện tại và giới hạn

`verify_facebook_session()` loại URL login/checkpoint/challenge/disabled/suspended, yêu cầu cookie `c_user`, và loại các login input đang hiển thị. Tuy nhiên chưa yêu cầu bằng chứng DOM đăng nhập tích cực, chưa so UID phiên với UID đầu vào; lỗi kiểm tra locator có thể bị bỏ qua.

Một trang rỗng cùng cookie `c_user` cũ vẫn có thể qua helper. Vì vậy đây chưa phải bảo đảm LIVE mạnh trong mọi trường hợp mạng/UI.

`login_facebook_user_pass()` trả ba chuỗi SUCCESS, INVALID, TECHNICAL_ERROR. Nhưng caller hiện vẫn có nhánh xử lý mọi kết quả khác SUCCESS như invalid login rồi gắn DIE. Timeout/network trong fallback RAW vì vậy vẫn có nguy cơ bị chuyển DIE. Đây là sai lệch hiện tại, không phải nguyên tắc mong muốn.

### 7.4. Checkpoint

Watcher poll và guard kiểm tra trong tác vụ đều có thể phát hiện checkpoint. `stop_checkpoint_account()` lưu lý do, latch trạng thái, ghi danh sách riêng và ngắt account đó. Các account khác không phải dừng theo. Latch chỉ được reset khi đi vào vòng kiểm tra mới theo logic state.

Không có chức năng tự vượt checkpoint mọi loại. Khi tài khoản gặp yêu cầu xác minh, không nên hiểu code sẽ giải quyết tất cả tự động.

## 8. Create Page: luồng chi tiết

Nguồn: [run_create_page](E:/FacebookTool_Project/client_app.py:5801).

### 8.1. Pre-flight và kế hoạch

Target Page dùng `page_name|category`. Chỉ có tên thì dùng fallback `Blog cá nhân`. Nếu chưa nhập đủ cấu hình, `build_create_page_plans()` bổ sung tên ngẫu nhiên và danh mục fallback theo behavior hiện tại. Không còn mặc định coi mọi danh sách target thiếu là phải dừng với “cần N cấu hình nhưng có 0”.

Validation chạy trước browser cho các cấu hình rõ ràng không hợp lệ. Mỗi lần tạo có Page context và job ID riêng: owner/account, tên, category, proxy, flow state, submitted, các định danh đã gặp, kết quả và retry.

Category được lấy từ kế hoạch Page hiện tại. Không mặc định ghi đè category người dùng bằng `Blog`. Cùng một danh sách template có thể dùng cho nhiều account, nhưng context/job/outcome của mỗi account riêng.

### 8.2. Các bước DOM

1. Guard session/checkpoint; mở `facebook.com/pages/creation/`.
2. Đợi input tên theo selector cấu trúc trước, có fallback ngôn ngữ. Nếu không thấy có nhánh screenshot/debug/reload rồi thử lại.
3. Điền tên; dùng helper typing và xử lý thông báo tên không hợp lệ. Một nhánh làm sạch tên có thể thay nội dung input; tên job gốc vẫn cần được đối chiếu ở verification.
4. Điền category của Page; chọn suggestion, kiểm tra lựa chọn, fallback alias/selector nếu cần.
5. Đợi nút submit có thể bấm; click tạo. Đặt `submitted=True` cho job đó. Không coi click là SUCCESS.
6. Poll trạng thái sau submit: session invalid, lỗi policy/rate, giao diện onboarding hoặc thông báo tạo xong gắn với tên Page.
7. Nhận diện thiết lập Page; click vùng trống an toàn, có nhánh điền bio; đi qua Next/Done/Skip hữu hạn, rồi click ngoài và Escape theo helper. Đây không phải bảo đảm mọi bản UI Facebook đều hoàn tất onboarding.
8. Thu Page identity và xác minh bằng job/account hiện tại.
9. Không có chứng cứ đúng Page: FAILED, không ghi success; ở nhánh chưa rõ sau submit có thể dừng chuỗi để tránh tạo trùng.
10. Có evidence hợp lệ: ghi success dưới lock, chống trùng; chỉ sau ghi hợp lệ mới tăng count và record outcome.
11. Chưa đạt mục tiêu và còn kế hoạch: chờ Delay Page, lướt Feed, rồi mới tạo Page kế tiếp.

Nếu Facebook báo “was created” nhưng vẫn nằm ở `/pages/creation/`, thông báo đó là tín hiệu chuyển bước, không tự đủ để ghi success khi chưa thu được định danh phù hợp.

### 8.3. Điều kiện SUCCESS

Nguồn định danh có thể là URL/canonical hợp lệ, Page ID từ DOM/deep link được helper nhận diện. `verify_page_job_evidence()` còn đối chiếu:

- Job đã submit, thuộc đúng account/owner.
- Page ID/URL hợp lệ, không trùng UID cá nhân hoặc định danh trước của job.
- Tên hiển thị khớp tên Page trong job sau chuẩn hóa.
- Canonical và URL/identity không mâu thuẫn theo dữ liệu đang có.

Chỉ chuỗi “manage page”, page load thành công, không exception hoặc hết nút thiết lập không phải bằng chứng SUCCESS.

Không xác minh được có thể là đã tạo thật nhưng code chưa đọc được ID; tool vẫn ghi FAILED thay vì đoán thành công. Đây là lựa chọn tránh false success, không đồng nghĩa Facebook chắc chắn chưa tạo Page.

### 8.4. Ghi kết quả và chống trùng

`save_created_page_success()` dùng `RESULT_FILE_LOCK`, đọc các identity đã lưu, so ID/URL rồi ghi `created_pages.csv` và `created_pages_success.txt`. Duplicate không được tăng count. Lock là trong process, không phải khóa chung giữa nhiều app đang chạy.

Hai file success không phải một transaction filesystem có rollback nguyên tử. Nếu một lần ghi lỗi giữa chừng, chưa có cam kết cả hai file đồng bộ tuyệt đối.

`create_page_results.csv` lưu cả SUCCESS/FAILED/ERROR: timestamp, account, page_name, category, page_url/page_id, proxy, reason, technical_error, retry_count, flow_state, owner_account_id và page_job_id.

`build_create_page_result()` chuẩn hóa result; `transition_page_context()` quản lý bước. Business failure không tự làm account DIE nếu phiên vẫn hợp lệ.

### 8.5. Retry

`retry_create_page_operation()` chỉ thử lại lỗi tạm thời của thao tác phù hợp, số lần hữu hạn với exponential backoff. Timeout/UI chậm có thể retry; session không hợp lệ hoặc policy rejection dừng nhánh theo phân loại. Sau click submit không tự blind retry tạo Page chỉ để đủ count.

Vòng lặp đi qua kế hoạch hữu hạn, không chạy vô hạn cho tới khi đạt chỉ tiêu. Các Page lỗi có thể làm cuối cùng thiếu target_count.

### 8.6. Countdown và Feed giữa các Page

`wait_between_page_jobs()` chọn một khoảng nghỉ từ min/max Delay Page đang cấu hình, dùng monotonic deadline và một task countdown cập nhật còn lại khoảng mỗi giây.

Chuyển về profile cá nhân, mở Feed, cuộn theo khoảng thời gian còn lại, không chủ động reaction trong helper chờ này. Guard Stop/checkpoint/cửa sổ bị đóng trước khi tạo tiếp. `finally` hủy timer và xóa chỉ báo hẹn.

Đây là khoảng nghỉ giữa Page, không phải lịch hẹn cố định mỗi ngày. Thời gian mở/chuyển trang tiêu thụ cùng budget; không cộng thêm một lần delay đầy đủ khác sau khi lướt.

## 9. Kết bạn

### 9.1. Ba nguồn

- `run_add_by_name()`: tìm người theo tên/từ khóa; nếu không có dùng dữ liệu mẫu hiện có, cuộn/đổi search khi không có tiến triển.
- `run_add_by_group()`: vào members của nhóm mục tiêu, tìm vùng thao tác người, số vòng hữu hạn.
- `run_add_by_uid()`: đi tới từng UID/profile URL, lưu `friend_actions.csv` cho kết quả nhánh này.

### 9.2. Xác nhận lời mời

`click_and_confirm_friend_request()` không chỉ click rồi tăng bộ đếm. Nó lấy vùng thao tác gắn với đúng người nhận, snapshot các link/control/state, kiểm tra đã friend/pending hay chưa, rồi theo dõi trạng thái sau click.

Có dữ liệu cấu trúc như friendship status và scope/target để tránh dùng nút của người B cho người A. Text đa ngôn ngữ là fallback. Nút biến mất đơn độc không đủ chứng minh gửi thành công. Attempt set theo account ngăn lặp một lời mời chưa được xác nhận.

Kết quả bao gồm đã gửi, đã có/pending, không xác minh hoặc lỗi; `record_friend_outcome()` đưa về SUCCESS/SKIPPED/FAILED/ERROR. Chỉ outcome gửi đã xác minh mới tăng bộ đếm.

Các fallback ngôn ngữ hiện có giúp nhiều locale nhưng không thể bảo đảm mọi layout/ngôn ngữ mới của Facebook hoạt động. Không có điều kiện “proxy US thì luôn dùng English”.

## 10. Ghép Page / thêm admin

`select_page_admin_job()` chọn target gắn STT/account hoặc wildcard; nhận Page URL hoặc AUTO và account đích. AUTO dùng Page đã xác minh của chính account, không lấy Page tùy ý từ account khác.

`run_add_page_admin()` mở Page access/settings, guard đúng Page reference, mở thêm người, tìm theo UID/tên, xác minh search result đúng target rồi chọn cấp quyền. Nếu có password prompt, ghi PENDING thay vì giả định cấp quyền xong.

Sau submit, phải còn evidence đúng Page + đúng target + feedback cấp quyền phù hợp. Kết quả phân biệt ASSIGNED, INVITED, PENDING, FAILED, ERROR và ghi `page_admin_jobs.csv`.

Tên tham số có Page/BM nhưng code này không chứng minh một hệ thống Business Manager hoàn chỉnh. `business_id` trong result hiện có thể trống; không nên đọc việc thêm Page admin thành “đã thêm tài sản vào BM” nếu không có nhánh xác minh BM tương ứng.

## 11. Các tác vụ còn lại và code ít/không được gọi

### 11.1. Tương tác trước tác vụ chính

Tùy options, worker có thể mở web ngoài, lướt Feed, xem Reels/review, Story, thông báo, reaction Messenger, tương tác Fanpage hoặc hủy lời mời cũ. Thao tác trước Create Page không phải phép tăng độ tin cậy được đo lường; code không có cam kết các hoạt động này giúp tránh giới hạn Facebook.

`human_type()` gõ ký tự có delay và có nhánh gõ sai/xóa; `human_click()` dùng bounding box và tọa độ bên trong; `safe_action_click()` thử lại hữu hạn khi phần tử/DOM thay đổi. Chúng là cách tương tác hiện tại, không phải bằng chứng Facebook sẽ coi là người thật.

### 11.2. Thứ tự module trong worker

Nếu bật nhiều mode, chúng chạy tuần tự trong cùng account theo thứ tự nhánh code, không theo thứ tự người dùng tick:

| Thứ tự | Mode | Hàm | Trách nhiệm |
|---:|---|---|---|
| 1 | by_name | run_add_by_name | Kết bạn qua tìm người. |
| 2 | by_group | run_add_by_group | Kết bạn qua members nhóm. |
| 3 | by_uid | run_add_by_uid | Kết bạn qua profile/UID. |
| 4 | join_group | run_join_groups | Mở nhóm và thao tác tham gia. |
| 5 | auto_post | run_auto_post | Đăng nội dung lên trang cá nhân. |
| 6 | auto_inbox | run_auto_inbox | Nhắn tin theo danh sách mục tiêu. |
| 7 | seed_group | run_seed_group | Tương tác/bình luận trong nhóm. |
| 8 | change_bio | run_change_bio | Sửa tiểu sử. |
| 9 | change_avatar | run_change_avatar | Upload ảnh đại diện từ file. |
| 10 | invite_group | run_invite_friends_to_group | Mời bạn vào nhóm. |
| 11 | scrape_uid | run_scrape_uid_post | Lấy UID từ tương tác bài viết. |
| 12 | create_page | run_create_page | Luồng Create Page có context/result riêng. |
| 13 | post_page | run_post_page | Đăng nội dung lên Page. |
| 14 | seed_live | run_seed_live | Tương tác livestream. |
| 15 | change_pass | run_change_password | Đổi password qua Accounts Center. |
| 16 | enable_2fa | run_enable_2fa | Thao tác bật 2FA, lưu secret nếu lấy được. |
| 17 | logout_sessions | run_logout_other_sessions | Đăng xuất các phiên khác. |
| 18 | add_page_admin | run_add_page_admin | Thêm/cấp quyền Page. |
| 19 | update_page_name | run_update_page_info | Sửa tên Page. |
| 20 | invite_like_page | run_invite_friends_like_page | Mời bạn thích Page. |
| 21 | inbox_commenters | run_inbox_post_commenters | Lấy người bình luận và nhắn tin. |
| 22 | post_joined_groups | run_post_joined_groups | Đăng lên nhóm đã tham gia. |
| 23 | comment_with_image | run_comment_with_image | Bình luận kèm upload ảnh. |
| 24 | scrape_group_members | run_scrape_group_members | Thu thành viên nhóm từ UI. |
| 25 | scrape_contacts | run_scrape_contact_info | Thu contact hiển thị trên profile. |

UI hiện chỉ đưa ra 12 mode chính: kết bạn ba loại, Create Page, post Page, admin Page, đổi tên Page, mời like Page, tham gia nhóm, đăng cá nhân, đổi bio, đổi avatar. Có nhánh worker nhưng không có checkbox hiện tại không đồng nghĩa người dùng đang chạy nhánh đó.

`filter_targets_for_mode()` nhận prefix `mode:...`; nếu có target riêng của mode thì dùng chúng, nếu không giữ nhánh target chung để tương thích. Đây không phải schema riêng hoàn chỉnh cho mọi mode.

Một số module cũ dựa nhiều vào text selector và thông báo sau click, không có verification mạnh như Create Page/friend helper. Không được suy rộng điều kiện SUCCESS của Create Page cho tất cả module.

### 11.3. Code còn lại ngoài luồng batch hiện tại

Các hàm reg Facebook bằng Hotmail, reg/login TikTok, reg Instagram, tương tác video TikTok vẫn tồn tại trong source nhưng không có lời gọi trong worker/UI hiện tại được xác định. Chúng là code còn lại, không phải chức năng đang tự chạy nền.

Tiện ích quản lý riêng gồm kiểm tra UID, mở profile, lấy token và tạo mã TOTP. Kiểm tra UID qua Graph picture chỉ đưa UNKNOWN/ERROR và yêu cầu login để kết luận, không chứng minh LIVE chỉ vì UID có ảnh.

## 12. State, nhật ký, kết quả và export

### 12.1. AccountStateStore

Store có RLock và state riêng theo STT/account_id. State chứa dữ liệu parser cùng status, current_action, logs/history_logs, tasks, last_task_result, proxy/effective_proxy, countdown, checkpoint latch và friend attempts.

Sync nối lại lịch sử theo account identity. Getter trả snapshot các collection để giảm việc sửa chung ngoài lock. Logs trong RAM được giới hạn, khi vượt 5000 giảm về khoảng 4500. Global logs có lock/giới hạn riêng.

`record_task()` lưu kết quả từng module, giữ FAILED/ERROR thay vì cho success sau che lỗi trước. `task_result_status()` có ưu tiên ERROR, FAILED, RUNNING, PENDING, SUCCESS, SKIPPED. Tổng task là số task, không phải luôn bằng số account.

Các task results: PENDING, RUNNING, SUCCESS, FAILED, ERROR, SKIPPED. Các Page flow states thêm VALIDATING, SESSION_CHECK, OPEN_CREATE_PAGE, FILL_PAGE_NAME, SELECT_CATEGORY, SUBMITTING, VERIFYING, CANCELLED.

### 12.2. AccountHistoryStore

SQLite có hai bảng:

- `accounts`: account_id khóa chính, status/task/action gần nhất, thời điểm, lỗi/checkpoint, tóm tắt Page/friend, proxy label và tasks JSON.
- `events`: id tăng dần, account_id, timestamp, module, event_type, result, message; index theo account/id.

`save()` bỏ credential keys khỏi tasks, redact thông tin nhạy cảm trong action/message và chỉ lưu endpoint proxy không auth. Upsert account và append event nếu khác event ngay trước. `load()` đọc state gần nhất và tối đa 500 event, ghép thành log lịch sử.

Không lưu raw line/password/2FA/cookie/token như credential columns trong DB này. RAM/UI và export có thể vẫn giữ chúng. Timestamps DB là UTC, nhiều log/UI dùng giờ máy.

### 12.3. Danh sách sau Create Page

RAM phân loại `completed`, `die`, `checkpoint`, reset khi bắt đầu đợt Create Page mới. Completed nghĩa là tạo đủ số Page mục tiêu theo record, không phải mọi account LIVE. DIE và CHECKPOINT tách nhau.

Khi xử lý kết thúc phù hợp, `get_processed_create_page_sources()` lấy raw sources của completed và die để xóa khỏi input. Không lấy checkpoint trong tập này. Việc hủy sớm có thể không đi tới bước dọn input cuối đợt. Lịch sử SQLite không bị reset chỉ vì reset danh sách kết quả RAM.

### 12.4. File sinh ra

| File dưới thư mục dữ liệu, trừ nơi ghi rõ | Dữ liệu |
|---|---|
| `settings.json` | Settings; một số field mã hóa. |
| `license.lic` | Key đã kích hoạt. |
| `account_history.db` | State/outcome/event đã redact theo helper. |
| `created_pages.csv` | Page success đã xác minh và chống trùng trong process. |
| `created_pages_success.txt` | Tóm tắt success. |
| `create_page_results.csv` | Result model của các lần tạo, kể cả FAILED/ERROR. |
| `create_page_<STT>_<account>.log` | Log Create Page riêng; account label làm sạch, giới hạn độ dài tên file. |
| `checkpoint_accounts.txt` | Dữ liệu account checkpoint; có thể chứa raw credentials. |
| `friend_actions.csv` | Kết quả kết bạn nhánh UID. |
| `page_admin_jobs.csv` | Result cấp quyền/Page admin và reason. |
| `browser_profiles/` | Profile persistent dùng tiện ích mở thủ công. |
| Các screenshot lỗi PNG | DOM đang hiển thị khi lỗi; có giới hạn số file theo helper. |
| `2fa_keys_saved.txt` | Secret 2FA nếu nhánh cũ bật và lấy được. |
| `group_members_scraped.txt`, `contacts_scraped.txt`, `scraped_post_uids.txt` | Kết quả các nhánh thu dữ liệu tương ứng. |
| `reg_facebook_success.txt`, `reg_tiktok_pending.txt`, `reg_instagram_success.txt` | Output của code reg cũ nếu được gọi; không phải batch chính tự tạo các file này. |
| `update_temp.exe`, `updater.bat`, `update_restart_error.log` | Download/thay EXE/restart và lỗi update. |
| XLSX/CSV tại nơi người dùng chọn | Export quản lý/kết quả. |

### 12.5. Excel và thông tin nhạy cảm

`write_create_page_results_xlsx()` dùng openpyxl, tạo sheet LIVE/DIE theo loại export, dòng tiêu đề màu, freeze A2, wrap text và filter. Schema hiện tại:

```text
A STT | B UID | C Password | D Status | E Page đã tạo
F Chỉ tiêu Page | G Kết quả/Lý do | H Thời gian | I Dữ liệu gốc
```

Status hiện là cột D, không phải C. Raw line ở I có thể chứa cookie/token; password ở C là dữ liệu thật theo record. Filter/width đang chỉ cấu hình tới tám cột, dù schema chín cột: một giới hạn formatting hiện tại.

CSV quản lý cũng chứa password/2FA theo schema. Copy raw, screenshot và file checkpoint không tự được bảo vệ bởi redaction SQLite. Người có file/clipboard có thể thấy dữ liệu đăng nhập; cần quản lý quyền truy cập các output này.

## 13. Dừng, lỗi và khôi phục nút

`stop_bot()` đặt stop flags, đổi UI thành đang dừng và gửi cancel vào event loop bằng `call_soon_threadsafe`. `_cancel_worker_tasks()` cancel các task chưa xong.

Worker có guard trong các bước và `finally` đóng watcher/browser. Task còn RUNNING được finalize sang SKIPPED khi Stop hoặc ERROR ở lỗi phù hợp; không giữ RUNNING vô thời hạn theo nhánh finalize được gọi. Task đã success không bị biến thành success giả cho phần còn lại.

`run_process()` ghi `run_error` khi exception thoát khỏi main_worker. `finish_run()` chờ thread kết thúc rồi khôi phục Bắt đầu, vô hiệu Dừng, reset pointers và hiển thị đỏ nếu run_error, vàng nếu Stop, xanh nếu không có lỗi top-level.

Màu xanh “Hoàn thành” chỉ là vòng chạy kết thúc không có top-level error đã truyền ra, không phải tất cả account/task SUCCESS. Các exception account được gather có thể không thành run_error tổng.

`on_close()` lưu settings, stop và chờ hữu hạn trước destroy cửa sổ. Thread automation là daemon. Không có bảo đảm hard-kill mọi browser process nếu cleanup đang treo hoặc tài nguyên chưa được trả từ browser factory.

## 14. Auto Update hiện tại

`check_for_updates()` đọc JSON metadata trên URL cấu hình, so version bằng tuple số. Phiên bản mới hơn mới mở popup changelog; equal + người dùng bấm Kiểm tra Update hiển thị đang dùng bản mới nhất; equal ở background thì im lặng.

URL download phải vượt trusted HTTPS/GitHub URL validation, hash phải đúng định dạng. Source mode vẫn xem changelog và tải thủ công được nhưng guard không cho self-update. Chỉ frozen EXE và basename không phải python/pythonw/py được phép.

Mandatory của packaged app khóa X/không có Để sau; non-mandatory có Để sau. Source mode không khóa developer bằng mandatory. Footer nút tách vùng changelog.

```text
Popup -> worker download update_temp.exe -> progress qua UI queue
 -> kiểm tra MZ + SHA256 -> guard self-update lại
 -> tạo updater.bat -> chạy helper ẩn -> đóng app cũ
 -> chờ process cũ kết thúc -> replace thành công
 -> restart với PYINSTALLER_RESET_ENVIRONMENT=1
    và loại _PYI_*/_MEIPASS2 khỏi environment mới
 -> dọn updater/temp; lỗi restart ghi log/thông báo mở tay
```

Restart chỉ sau replace. Không bypass PyInstaller security. Restart fail không có mục tiêu phá EXE vừa cài hoặc rollback nhầm; có đường báo mở thủ công. Helper theo dõi lỗi khởi động trong khoảng ngắn, không xác minh mọi chức năng app mới chạy ổn định lâu dài.

Các exception check metadata có nhánh im lặng, nên không thấy popup cũng có thể là check thất bại. Tài liệu này không thực thi update hay probe EXE.

## 15. release.ps1

Script hiện dùng exit code của native command, không coi mọi stderr là thất bại. Ví dụ `git fetch` in `From ...` nhưng exit code 0 vẫn thành công.

Thứ tự thực tế:

1. Nhận version/changelog, kiểm tra file cần có và `git`, `gh`, `python` trong PATH.
2. Kiểm tra gh login, nhánh main, fetch origin/main và tags, không đứng sau remote.
3. Từ chối tag local/remote hoặc release đã tồn tại; lấy repository identity.
4. Lưu nội dung source cũ, thay duy nhất dòng CURRENT_VERSION khớp pattern.
5. Chạy pytest; exit code quyết định gate. Passed/failed/skipped đọc động chỉ để log, không expected count cố định. Collection/import/no tests theo exit code pytest sẽ dừng.
6. Xóa output build liên quan, build bằng spec hiện có, yêu cầu EXE tồn tại và MZ hợp lệ, tính SHA256.
7. Stage source bằng `git add -A`, loại `version.json` khỏi staging; commit/push main, tạo annotated tag và push tag.
8. Tạo Draft Release, upload EXE, download asset vào temp và so hash với local.
9. Đúng hash mới publish và đặt Latest.
10. Sau publish mới cập nhật version/download_url/sha256/changelog trong version.json, giữ field khác như mandatory; commit/push metadata.

Fail trước commit source thì khôi phục nội dung client_app ban đầu. Fail sau commit/tag/draft có thể để lại các bước remote đã hoàn tất; đây không phải transaction tự rollback toàn GitHub. Tag/release cũ không bị ghi đè, nên không blind retry cùng version nếu đã tạo một phần.

`git add -A` có thể đưa cả thay đổi khác đang có vào commit source, không chỉ dòng version. Khi sử dụng script, cần xem worktree trước. Tài liệu này KHÔNG chạy script.

| Hàm PowerShell | Công việc |
|---|---|
| Get-RequiredCommand | Kiểm tra command tồn tại. |
| Invoke-NativeCapture | Capture stdout/stderr, exit code; điều chỉnh rồi khôi phục error preferences. |
| Invoke-NativeChecked | Log label/output; throw khi native exit khác 0. |
| Write-Utf8NoBom | Ghi text UTF-8 không BOM. |
| Set-JsonProperty | Thay/thêm property nhưng giữ các property khác. |
| Remove-PathWithRetry | Dọn output với số lần thử hữu hạn. |
| Invoke-PytestGate | Chạy pytest, lấy summary động và áp gate exit code. |

## 16. Cloudflare license worker và Telegram admin

### 16.1. Routes

| Route | Vai trò |
|---|---|
| POST `/validate` | Kiểm key, HWID, hạn và trạng thái; có thể bind HWID lần đầu. |
| POST `/telegram/webhook` | Nhận lệnh quản lý license, kiểm secret header và admin chat. |
| GET `/telegram/status` | Báo cấu hình đã có hay chưa bằng boolean, không trả secret. |
| GET `/health` | Health JSON. |
| Route khác | 404. |

### 16.2. License data

Bảng `licenses`: `key_hash`, `key_hint`, `hwid`, `expires_at`, `status`, `created_at`, `activated_at`. Server lưu SHA256 key và hint, không lưu key gốc như credential column. Key mới được gửi về admin qua Telegram.

`validateLicense()` kiểm JSON/định dạng key/HWID, lấy record, kiểm active/hạn/binding; nếu chưa bind thì UPDATE HWID. Check và update là các thao tác riêng, không phải conditional bind atomic được chứng minh bởi code hiện tại.

### 16.3. Telegram commands

- `/create <days>`: tạo key ngẫu nhiên, chống trùng hash, lưu hạn, gửi key.
- `/activate <key> <hwid>`: bind key active với mã máy.
- `/revoke <key>`: chuyển revoked.
- `/check <key>`: trả hint/HWID/hạn/status.
- Lệnh không khớp: trả hướng dẫn.

Chỉ chat admin cấu hình được xử lý và webhook phải có đúng secret. `telegramSend()` gọi API Telegram, lỗi HTTP thì throw để handler báo lỗi. Đây là bot cấp phép, khác với bot nhận cảnh báo batch từ client.

### 16.4. Hàm JS

| Hàm | Trách nhiệm |
|---|---|
| json | Response JSON và HTTP status. |
| normalizeKey | Trim/uppercase key. |
| isLicenseKey | Validate format key. |
| sha256 | Hash bằng WebCrypto. |
| randomKey | Tạo key ngẫu nhiên bằng crypto. |
| parseDuration | Parse số ngày trong khoảng cho phép. |
| validateLicense | Luồng validate/bind như trên. |
| telegramSend | HTTP POST gửi tin, kiểm response. |
| handleTelegram | Auth webhook/admin, dispatch lệnh và DB writes. |
| export default.fetch | Router theo method/path, chọn handler. |

Schema SQL tạo bảng/index; wrangler nối binding DB và cấu hình. README mô tả triển khai, không phải một đoạn runtime được desktop tự gọi.

## 17. Tests và mức độ xác minh

Tests được chia thành logic parser/cookie/proxy/version; isolation/log/history; session/checkpoint; Page evidence/category/count; friend scope; stop/lifecycle/countdown; theme/export; updater/restart helpers. Có fixtures, fake page/locator/browser/root và các callback mô phỏng ở bên trong test.

Test PASS chứng minh case mô phỏng thỏa assertions, không chứng minh selector đang match mọi tài khoản Facebook thật. Mocks cần phản ánh DOM/network thực tế; thiếu case có thể để bug tồn tại dù suite xanh.

Probe restart là chương trình riêng có thể thao tác executable thử nghiệm; không phải mở app production bình thường và không được tự chạy trong lúc viết tài liệu.

**Lần tạo tài liệu này:** chỉ đọc/đối chiếu source, không chạy pytest, không runtime Facebook, không thử packaged EXE. Không lấy số test trong một lần trước làm số test cố định cho tương lai.

## 18. Những điểm cần hiểu đúng trước khi chạy lâu dài

| Điểm đang tồn tại | Ý nghĩa thực tế |
|---|---|
| Start flag đặt trước reload | Snapshot có thể dùng state/proxy cũ thay vì raw input mới. |
| Parser heuristic | Có thể nhầm password/2FA; chưa thực hiện strict contract năm cột. |
| Caller RAW login gom technical failure | Timeout/network vẫn có nhánh bị đánh DIE. |
| Verify session thiếu positive evidence | Có nguy cơ false LIVE khi DOM rỗng/cookie cũ. |
| Cleanup lúc mở browser chưa đầy đủ | Cancel/error trước khi trả resources có thể treo/leak; close lỗi không luôn bounded. |
| Các flow cũ verification yếu | Không phải mọi module có tiêu chuẩn success như Create Page. |
| Một số output chứa raw/password/2FA | Redaction SQLite không bảo vệ toàn bộ exports. |
| SUCCESS ghi nhiều file | Lock nội bộ không tạo transaction chung hoặc bảo vệ nhiều app instance. |
| “Hoàn thành” tổng khác task SUCCESS | Cần đọc từng account/task, không chỉ nhãn xanh. |
| Multi-locale có fallback | Chưa bảo đảm mọi ngôn ngữ/UI; locale metadata parser chưa nối đầy đủ. |

Các điểm này được mô tả để tài liệu phản ánh đúng hiện trạng, không phải đã được sửa trong công việc này.

## 19. Thuật ngữ nhanh

| Thuật ngữ | Cách hiểu trong project |
|---|---|
| Raw line | Dòng tài khoản gốc được parser giữ. |
| Account state | Dữ liệu/tiến trình/log của một account trong RAM. |
| Session | Cookie + trạng thái browser dùng cho đăng nhập. |
| Batch/đợt | Nhóm account chạy trước khi qua nhóm kế tiếp. |
| Worker/semaphore | Công việc async và giới hạn số account cùng xử lý. |
| ContextVar | Nhãn account riêng theo luồng async để route log. |
| Browser context | Không gian cookies/storage của Playwright. |
| Task result | Kết quả tác vụ, không đồng nghĩa account status. |
| Page identity | URL/ID Page làm bằng chứng thay vì chỉ click/UI text. |
| Pre-flight | Kiểm input/kế hoạch trước các thao tác browser tốn tài nguyên. |
| Headless | Browser không hiển thị cửa sổ; vẫn có tiến trình chạy. |
| Frozen | Chạy executable đóng gói, khác chạy source bằng Python. |
| SHA256 | Hash so nội dung EXE download/release với metadata. |

## Phụ lục A. Danh mục class và từng hàm Python

Mỗi mục có vị trí bắt đầu và khoảng dòng trong snapshot. Hàm lồng bên trong hàm khác được giữ đầy đủ vì chúng thực hiện callback, JS/script generation hoặc mô phỏng test. Mô tả ngắn trong danh mục phải đọc cùng các mục trên; docstring có thể nói ý định tốt hơn mức bảo đảm implementation thực tế.

### client_app.py

7563 dòng source; 257 khai báo hàm/callback, 6 class. Đây không phải số test cases.

| Class / vị trí | Vai trò |
|---|---|
| [`FriendRequestOutcome`](E:/FacebookTool_Project/client_app.py:180) (180-184) | Outcome lời mời có dữ liệu kèm. |
| [`FacebookCheckpointStopped`](E:/FacebookTool_Project/client_app.py:275) (275-276) | Exception chuyên biệt ngắt account khi checkpoint. |
| [`AccountStateStore`](E:/FacebookTool_Project/client_app.py:455) (455-671) | State/log/task store có lock. |
| [`LicenseCheckDialog`](E:/FacebookTool_Project/client_app.py:1976) (1976-2008) | Giao diện kích hoạt. |
| [`ImportAccountDialog`](E:/FacebookTool_Project/client_app.py:2077) (2077-2152) | Giao diện nhập account. |
| [`MainToolApp`](E:/FacebookTool_Project/client_app.py:2154) (2154-7537) | Controller/UI/worker automation desktop. |

| Hàm / vị trí | Trách nhiệm hoặc mục tiêu kiểm thử |
|---|---|
| [`output_path`](E:/FacebookTool_Project/client_app.py:60) (60-61) | Ghép tên output với thư mục dữ liệu cục bộ. |
| [`resource_path`](E:/FacebookTool_Project/client_app.py:63) (63-65) | Chọn đường dẫn resource ở source hoặc bundle PyInstaller. |
| [`generate_random_person_name`](E:/FacebookTool_Project/client_app.py:87) (87-93) | Tự động kết hợp ngẫu nhiên tạo ra hơn 500+ tên người Việt Nam thực tế |
| [`configure_account_table_style`](E:/FacebookTool_Project/client_app.py:158) (158-164) | Đặt font, row height và màu chọn dòng Treeview theo theme. |
| [`task_result_status`](E:/FacebookTool_Project/client_app.py:167) (167-169) | Tổng hợp các task theo thứ tự ưu tiên kết quả. |
| [`page_wait_label`](E:/FacebookTool_Project/client_app.py:172) (172-177) | Định dạng số giây còn lại thành nhãn countdown. |
| [`FriendRequestOutcome.__new__`](E:/FacebookTool_Project/client_app.py:181) (181-184) | Tạo outcome lời mời kèm người nhận/lý do. |
| [`friend_profile_reference`](E:/FacebookTool_Project/client_app.py:187) (187-200) | Chuẩn hóa tham chiếu người nhận từ URL Facebook. |
| [`classify_friend_controls`](E:/FacebookTool_Project/client_app.py:203) (203-210) | Đọc các control để phân biệt friend/pending/add/unknown. |
| [`normalize_ui_text`](E:/FacebookTool_Project/client_app.py:222) (222-223) | Chuẩn hóa text dùng cho so sánh UI. |
| [`page_creation_notice_matches`](E:/FacebookTool_Project/client_app.py:226) (226-236) | Đối chiếu notice tạo Page với tên của job hiện tại. |
| [`verify_page_job_evidence`](E:/FacebookTool_Project/client_app.py:251) (251-269) | Kiểm evidence Page thuộc job đã submit, đúng owner/tên/identity. |
| [`detect_facebook_account_state [async]`](E:/FacebookTool_Project/client_app.py:279) (279-304) | Phân loại dấu hiệu URL/DOM của account, gồm checkpoint. |
| [`is_page_policy_rejected`](E:/FacebookTool_Project/client_app.py:307) (307-312) | Phát hiện các thông báo policy ngăn tạo Page. |
| [`save_checkpoint_account`](E:/FacebookTool_Project/client_app.py:315) (315-324) | Ghi raw account checkpoint vào danh sách riêng dưới lock. |
| [`split_account_batches`](E:/FacebookTool_Project/client_app.py:334) (334-337) | Chia danh sách thành từng nhóm theo batch size. |
| [`effective_account_worker_count`](E:/FacebookTool_Project/client_app.py:340) (340-350) | Giới hạn số account chạy đồng thời theo mode/config. |
| [`account_status_for_failure`](E:/FacebookTool_Project/client_app.py:353) (353-354) | Map loại lỗi sang DIE hoặc ERROR; caller cần truyền đúng loại. |
| [`normalize_account_source_line`](E:/FacebookTool_Project/client_app.py:357) (357-359) | Normalize only the UI number prefix so account data remains byte-for-byte intact. |
| [`account_display_name`](E:/FacebookTool_Project/client_app.py:362) (362-370) | Return a stable label for parsed input and older account-state snapshots. |
| [`is_invalid_facebook_account_url`](E:/FacebookTool_Project/client_app.py:373) (373-378) | Nhận diện URL phiên bị chặn/không hợp lệ. |
| [`keep_unprocessed_account_lines`](E:/FacebookTool_Project/client_app.py:381) (381-390) | Loại input đã xử lý khỏi danh sách, giữ các dòng còn lại. |
| [`write_create_page_results_xlsx`](E:/FacebookTool_Project/client_app.py:393) (393-452) | Write LIVE/DIE account results to a styled Excel workbook. |
| [`AccountStateStore.__init__`](E:/FacebookTool_Project/client_app.py:456) (456-459) | Khởi tạo dict state, RLock và history store. |
| [`AccountStateStore._persist`](E:/FacebookTool_Project/client_app.py:461) (461-463) | Gửi snapshot/sự kiện sang store lịch sử. |
| [`AccountStateStore.sync`](E:/FacebookTool_Project/client_app.py:465) (465-522) | Đồng bộ account input với state và lịch sử theo định danh. |
| [`AccountStateStore.indexes`](E:/FacebookTool_Project/client_app.py:524) (524-526) | Trả danh sách STT đang có trong store. |
| [`AccountStateStore.get`](E:/FacebookTool_Project/client_app.py:528) (528-542) | Trả snapshot state và bản sao collection cần thiết. |
| [`AccountStateStore.update`](E:/FacebookTool_Project/client_app.py:544) (544-572) | Cập nhật state hợp lệ dưới lock, bảo vệ checkpoint latch. |
| [`AccountStateStore.set_proxy`](E:/FacebookTool_Project/client_app.py:574) (574-578) | Lưu proxy của đúng account. |
| [`AccountStateStore.mark_friend_attempt`](E:/FacebookTool_Project/client_app.py:580) (580-582) | Ghi nhận người nhận đã thử gửi lời mời theo account. |
| [`AccountStateStore.set_page_wait`](E:/FacebookTool_Project/client_app.py:584) (584-592) | Cập nhật remaining/next_page_at của account. |
| [`AccountStateStore.finalize_active_tasks`](E:/FacebookTool_Project/client_app.py:594) (594-607) | Đưa task đang hoạt động sang kết quả cuối khi dừng/lỗi. |
| [`AccountStateStore.record_task`](E:/FacebookTool_Project/client_app.py:609) (609-630) | Ghi trạng thái/detail/outcome module, giữ lỗi trước theo ưu tiên. |
| [`AccountStateStore.task_summary`](E:/FacebookTool_Project/client_app.py:632) (632-640) | Đếm các kết quả task của account/tập account. |
| [`AccountStateStore.append_log`](E:/FacebookTool_Project/client_app.py:642) (642-653) | Append log account, giới hạn RAM và persist event. |
| [`AccountStateStore.set_failure`](E:/FacebookTool_Project/client_app.py:655) (655-662) | Đặt failure category/status/detail vào đúng state. |
| [`AccountStateStore.summary`](E:/FacebookTool_Project/client_app.py:664) (664-671) | Đếm account theo status. |
| [`normalize_account_locale`](E:/FacebookTool_Project/client_app.py:760) (760-767) | Validate/chuẩn hóa locale; AUTO giữ lựa chọn trình duyệt. |
| [`normalize_account_timezone`](E:/FacebookTool_Project/client_app.py:770) (770-774) | Validate timezone được cấu hình. |
| [`split_account_metadata`](E:/FacebookTool_Project/client_app.py:777) (777-793) | Remove optional account metadata tokens without inferring them from the proxy. |
| [`browser_locale_options`](E:/FacebookTool_Project/client_app.py:796) (796-806) | Return browser locale settings; AUTO leaves Facebook/browser language untouched. |
| [`resolve_account_proxy`](E:/FacebookTool_Project/client_app.py:809) (809-815) | Use the proxy captured for this account; never borrow another account's proxy. |
| [`facebook_page_reference`](E:/FacebookTool_Project/client_app.py:818) (818-831) | Extract a Page reference from Page and Page-settings URLs. |
| [`page_reference_matches`](E:/FacebookTool_Project/client_app.py:834) (834-837) | So sánh hai tham chiếu Page đã chuẩn hóa. |
| [`locator_matches_account_target [async]`](E:/FacebookTool_Project/client_app.py:840) (840-864) | Verify a search result against the user-provided UID/name, independent of UI language. |
| [`version_tuple`](E:/FacebookTool_Project/client_app.py:866) (866-869) | Chuyển chuỗi version thành tuple số để so sánh đúng thứ tự. |
| [`parse_page_plan`](E:/FacebookTool_Project/client_app.py:872) (872-878) | Parse `page name\|category`; old one-column page names remain valid. |
| [`build_create_page_plans`](E:/FacebookTool_Project/client_app.py:881) (881-891) | Build the requested Page plans while preserving legacy auto-name behavior. |
| [`validate_create_page_targets`](E:/FacebookTool_Project/client_app.py:894) (894-908) | Validate explicit Page plans before any browser is launched. |
| [`filter_targets_for_mode`](E:/FacebookTool_Project/client_app.py:911) (911-934) | Return targets for one mode without discarding legacy unscoped entries. |
| [`build_create_page_result`](E:/FacebookTool_Project/client_app.py:937) (937-967) | Tạo record SUCCESS/FAILED/ERROR và các field output. |
| [`build_page_context`](E:/FacebookTool_Project/client_app.py:970) (970-982) | Tạo context/job Page riêng gồm owner, config, proxy, state. |
| [`transition_page_context`](E:/FacebookTool_Project/client_app.py:985) (985-1002) | Chuyển flow state và cập nhật dữ liệu/error của job. |
| [`classify_page_access_feedback`](E:/FacebookTool_Project/client_app.py:1005) (1005-1015) | Phân loại feedback cấp quyền thành assigned/invited/pending hoặc lỗi. |
| [`build_page_access_result`](E:/FacebookTool_Project/client_app.py:1018) (1018-1031) | Tạo record cấp quyền gắn account, Page và target. |
| [`save_page_access_result`](E:/FacebookTool_Project/client_app.py:1040) (1040-1041) | Ghi record Page/admin ra CSV chung dưới cơ chế lock. |
| [`page_identity_keys`](E:/FacebookTool_Project/client_app.py:1044) (1044-1052) | Chuẩn hóa khóa chống trùng ID/URL. |
| [`save_created_page_success`](E:/FacebookTool_Project/client_app.py:1055) (1055-1092) | So trùng rồi ghi hai output success dưới lock trong process; không transaction filesystem. |
| [`upgrade_page_result_header`](E:/FacebookTool_Project/client_app.py:1103) (1103-1120) | Nâng header kết quả cũ theo schema hiện tại khi cần. |
| [`save_create_page_outcome`](E:/FacebookTool_Project/client_app.py:1123) (1123-1126) | Chuẩn bị schema và append outcome Create Page dưới lock. |
| [`append_create_page_account_log`](E:/FacebookTool_Project/client_app.py:1129) (1129-1134) | Ghi file log Create Page riêng theo STT/account label. |
| [`is_transient_create_page_error`](E:/FacebookTool_Project/client_app.py:1137) (1137-1144) | Nhận diện exception kỹ thuật tạm thời được phép retry. |
| [`retry_create_page_operation [async]`](E:/FacebookTool_Project/client_app.py:1147) (1147-1162) | Retry transient pre-submit operations with bounded exponential backoff. |
| [`close_browser_resources [async]`](E:/FacebookTool_Project/client_app.py:1165) (1165-1175) | Close isolated resources on success, failure, or cancellation. |
| [`wait_for_locator_ready [async]`](E:/FacebookTool_Project/client_app.py:1178) (1178-1192) | Chờ phần tử hiển thị và sẵn sàng tương tác, kết hợp kiểm tra is_enabled() chuẩn xác. |
| [`select_page_admin_job`](E:/FacebookTool_Project/client_app.py:1195) (1195-1218) | Select an account-specific Page/admin mapping while preserving legacy input. |
| [`extract_facebook_page_identity`](E:/FacebookTool_Project/client_app.py:1221) (1221-1248) | Return a stable Page URL/ID from current or canonical Facebook URLs. |
| [`is_verified_page_identity`](E:/FacebookTool_Project/client_app.py:1251) (1251-1259) | Return True only when Facebook supplied a stable Page URL or Page ID. |
| [`append_csv_result`](E:/FacebookTool_Project/client_app.py:1262) (1262-1271) | Append one durable result row without interleaving concurrent workers. |
| [`is_trusted_update_url`](E:/FacebookTool_Project/client_app.py:1273) (1273-1280) | Kiểm URL download theo trusted HTTPS/GitHub executable rules. |
| [`get_self_update_target`](E:/FacebookTool_Project/client_app.py:1283) (1283-1290) | Reject source/interpreter; trả target chỉ khi packaged hợp lệ. |
| [`get_update_restart_environment`](E:/FacebookTool_Project/client_app.py:1293) (1293-1300) | Chuẩn bị môi trường PyInstaller mới, reset và loại biến kế thừa. |
| [`build_windows_update_restart_script`](E:/FacebookTool_Project/client_app.py:1303) (1303-1381) | Build the updater script that replaces and starts a fresh PyInstaller app. |
| [`build_windows_update_restart_script.batch_path`](E:/FacebookTool_Project/client_app.py:1305) (1305-1306) | Escape đường dẫn khi đặt trong batch command. |
| [`build_windows_update_restart_script.encoded_command`](E:/FacebookTool_Project/client_app.py:1311) (1311-1312) | Mã hóa PowerShell command nhúng cho helper Windows. |
| [`check_for_updates`](E:/FacebookTool_Project/client_app.py:1384) (1384-1566) | Kiểm tra bản mới và hiển thị cửa sổ cập nhật tùy chỉnh có thanh tiến trình |
| [`check_for_updates.show_update_dialog`](E:/FacebookTool_Project/client_app.py:1408) (1408-1556) | Dựng popup changelog/progress/footer, áp mandatory/source guard. |
| [`check_for_updates.show_update_dialog.start_download`](E:/FacebookTool_Project/client_app.py:1465) (1465-1544) | Khóa nút và khởi động worker tải nếu target được phép. |
| [`check_for_updates.show_update_dialog.start_download.download_worker`](E:/FacebookTool_Project/client_app.py:1482) (1482-1542) | Tải, kiểm MZ/hash/guard, tạo updater và chuyển sang helper restart. |
| [`get_hwid`](E:/FacebookTool_Project/client_app.py:1569) (1569-1601) | Lấy mã định danh phần cứng máy tính duy nhất và bảo mật |
| [`verify_license`](E:/FacebookTool_Project/client_app.py:1603) (1603-1628) | Xác thực license online bằng Cloudflare Worker API. |
| [`load_saved_license`](E:/FacebookTool_Project/client_app.py:1630) (1630-1636) | Đọc license an toàn; file hỏng hoặc không đọc được sẽ coi như chưa kích hoạt. |
| [`settings_cipher`](E:/FacebookTool_Project/client_app.py:1638) (1638-1642) | Tạo Fernet từ khóa dẫn xuất theo máy. |
| [`protect_setting`](E:/FacebookTool_Project/client_app.py:1644) (1644-1647) | Mã hóa chuỗi setting nhạy cảm. |
| [`unprotect_setting`](E:/FacebookTool_Project/client_app.py:1649) (1649-1656) | Giải mã setting hoặc trả dữ liệu legacy theo fallback. |
| [`normalize_cookie_input`](E:/FacebookTool_Project/client_app.py:1660) (1660-1689) | Normalize login cookies without changing the stored account input. |
| [`parse_cookies`](E:/FacebookTool_Project/client_app.py:1692) (1692-1719) | Tạo cookie objects dùng cho context từ chuỗi chuẩn hóa. |
| [`parse_proxy`](E:/FacebookTool_Project/client_app.py:1721) (1721-1761) | Parse endpoint/protocol/auth/IPv6 và validate port/auth. |
| [`reset_rotating_proxy`](E:/FacebookTool_Project/client_app.py:1763) (1763-1772) | Gửi yêu cầu đổi IP qua đường link API của nhà cung cấp Proxy xoay |
| [`fetch_proxy_from_api`](E:/FacebookTool_Project/client_app.py:1774) (1774-1829) | Tự động nhận diện Key hoặc Link API SuiProxy/TMProxy để lấy IP:Port mới nhất |
| [`spin_text`](E:/FacebookTool_Project/client_app.py:1830) (1830-1841) | Xử lý cú pháp Spin-Tax {A\|B\|C} để tạo nội dung ngẫu nhiên chống trùng lặp |
| [`generate_totp_code`](E:/FacebookTool_Project/client_app.py:1843) (1843-1859) | Tạo mã TOTP hiện tại từ secret Base32. |
| [`send_telegram_alert`](E:/FacebookTool_Project/client_app.py:1861) (1861-1874) | Gửi cảnh báo tức thì về Telegram Bot |
| [`parse_any_account_line`](E:/FacebookTool_Project/client_app.py:1876) (1876-1964) | Parser heuristic hiện tại; giữ raw nhưng chưa ép strict contract năm cột. |
| [`serialize_account_line`](E:/FacebookTool_Project/client_app.py:1968) (1968-1970) | Return the exact user-provided account line for lossless UI refresh/export. |
| [`serialize_account_lines`](E:/FacebookTool_Project/client_app.py:1973) (1973-1974) | Nối raw_line của các account thành text nhiều dòng. |
| [`LicenseCheckDialog.__init__`](E:/FacebookTool_Project/client_app.py:1977) (1977-1996) | Dựng cửa sổ HWID, nhập key và kích hoạt. |
| [`LicenseCheckDialog.activate`](E:/FacebookTool_Project/client_app.py:1998) (1998-2008) | Verify license, báo lỗi hoặc lưu key/gọi callback thành công. |
| [`get_installed_browser_path`](E:/FacebookTool_Project/client_app.py:2009) (2009-2024) | Tìm đường dẫn thực tế của Chrome hoặc Edge trên máy Windows |
| [`ImportAccountDialog.__init__`](E:/FacebookTool_Project/client_app.py:2079) (2079-2126) | Dựng dialog nhập account theo lựa chọn định dạng hiện tại. |
| [`ImportAccountDialog.process_import`](E:/FacebookTool_Project/client_app.py:2128) (2128-2152) | Đọc input, parse và chuyển raw accounts cho callback chính. |
| [`MainToolApp.auto_format_cookie_numbers`](E:/FacebookTool_Project/client_app.py:2155) (2155-2166) | Refresh the numbered table without rewriting the raw account input. |
| [`MainToolApp.__init__`](E:/FacebookTool_Project/client_app.py:2168) (2168-2219) | Khởi tạo UI, stores/locks/queue/flags; load settings và check update nền. |
| [`MainToolApp.post_ui`](E:/FacebookTool_Project/client_app.py:2221) (2221-2224) | Schedule a UI callback without calling Tkinter from a worker thread. |
| [`MainToolApp._drain_ui_queue`](E:/FacebookTool_Project/client_app.py:2226) (2226-2240) | Chạy các callback UI pending bằng Tk thread và hẹn poll tiếp. |
| [`MainToolApp._bounded_int`](E:/FacebookTool_Project/client_app.py:2243) (2243-2248) | Parse số nguyên, dùng fallback và clamp min/max. |
| [`MainToolApp.capture_run_config`](E:/FacebookTool_Project/client_app.py:2250) (2250-2314) | Read every Tk value once on the UI thread before automation starts. |
| [`MainToolApp._build_layout`](E:/FacebookTool_Project/client_app.py:2316) (2316-2405) | Dựng khung root, thanh điều hướng/theme/update và các tab. |
| [`MainToolApp.switch_tab`](E:/FacebookTool_Project/client_app.py:2407) (2407-2417) | Ẩn/hiện tab và đổi trạng thái nút điều hướng. |
| [`MainToolApp._create_card`](E:/FacebookTool_Project/client_app.py:2419) (2419-2424) | Tạo khung panel/UI helper theo theme. |
| [`MainToolApp._start_clock`](E:/FacebookTool_Project/client_app.py:2426) (2426-2433) | Khởi động đồng hồ giao diện. |
| [`MainToolApp._start_clock.update`](E:/FacebookTool_Project/client_app.py:2427) (2427-2432) | Cập nhật nhãn giờ và hẹn lần cập nhật kế tiếp. |
| [`MainToolApp.on_change_theme`](E:/FacebookTool_Project/client_app.py:2435) (2435-2437) | Áp theme được người dùng chọn. |
| [`MainToolApp.apply_theme`](E:/FacebookTool_Project/client_app.py:2439) (2439-2505) | Đổi toàn bộ màu sắc phần mềm theo Theme được chọn |
| [`MainToolApp.apply_theme.recolor_widget`](E:/FacebookTool_Project/client_app.py:2483) (2483-2495) | Đi qua cây widget và cập nhật màu/font phù hợp. |
| [`MainToolApp._build_tab_main`](E:/FacebookTool_Project/client_app.py:2509) (2509-2866) | Dựng input, options, table trạng thái, logs, tham số và điều khiển chạy. |
| [`MainToolApp._build_tab_main.toggle_all`](E:/FacebookTool_Project/client_app.py:2547) (2547-2548) | Tick/bỏ tick toàn bộ mode được UI quản lý. |
| [`MainToolApp._build_tab_main._on_canvas_configure`](E:/FacebookTool_Project/client_app.py:2561) (2561-2562) | Đồng bộ vùng cuộn/kích thước content canvas. |
| [`MainToolApp._build_tab_main._on_mousewheel`](E:/FacebookTool_Project/client_app.py:2565) (2565-2566) | Xử lý cuộn mouse wheel cho panel. |
| [`MainToolApp._build_tab_main.make_stat_box`](E:/FacebookTool_Project/client_app.py:2855) (2855-2861) | Dựng một ô tổng số của footer. |
| [`MainToolApp._build_tab_data`](E:/FacebookTool_Project/client_app.py:2869) (2869-3014) | Dựng bảng quản lý account, lọc, menu context và tiện ích. |
| [`MainToolApp._build_tab_data.make_btn`](E:/FacebookTool_Project/client_app.py:2896) (2896-2902) | Dựng nút tiện ích quản lý. |
| [`MainToolApp._build_tab_data.filter_table`](E:/FacebookTool_Project/client_app.py:2925) (2925-2932) | Lọc các dòng account theo lựa chọn UI. |
| [`MainToolApp._build_tab_data.show_context_menu`](E:/FacebookTool_Project/client_app.py:2971) (2971-2976) | Hiện menu khi thao tác trên bảng. |
| [`MainToolApp._build_tab_data.toggle_row_check`](E:/FacebookTool_Project/client_app.py:2981) (2981-2990) | Đổi dấu chọn của dòng account. |
| [`MainToolApp.copy_tree_data`](E:/FacebookTool_Project/client_app.py:3016) (3016-3041) | Copy dữ liệu cột/raw theo lựa chọn; có thể gồm bí mật. |
| [`MainToolApp.open_create_page_results_dialog`](E:/FacebookTool_Project/client_app.py:3042) (3042-3142) | Mở danh sách completed/die/checkpoint với copy/export. |
| [`MainToolApp.refresh_create_page_results_dialog`](E:/FacebookTool_Project/client_app.py:3144) (3144-3185) | Nạp lại rows/counters của cửa sổ kết quả. |
| [`MainToolApp.export_create_page_results_excel`](E:/FacebookTool_Project/client_app.py:3187) (3187-3215) | Chọn đường dẫn và gọi writer XLSX theo nhóm kết quả. |
| [`MainToolApp.remove_processed_create_page_accounts_from_input`](E:/FacebookTool_Project/client_app.py:3217) (3217-3242) | Loại raw sources completed/die khỏi textbox rồi refresh/save. |
| [`MainToolApp.update_footer_count`](E:/FacebookTool_Project/client_app.py:3246) (3246-3248) | Cập nhật số account trong footer. |
| [`MainToolApp.get_batch_size`](E:/FacebookTool_Project/client_app.py:3250) (3250-3253) | Đọc batch size hợp lệ từ UI/config. |
| [`MainToolApp.refresh_account_state_table`](E:/FacebookTool_Project/client_app.py:3255) (3255-3297) | Dựng lại bảng state cho batch đang xem. |
| [`MainToolApp.refresh_account_state_row`](E:/FacebookTool_Project/client_app.py:3299) (3299-3321) | Cập nhật row tương ứng account/status/task/countdown/action. |
| [`MainToolApp.refresh_state_summary`](E:/FacebookTool_Project/client_app.py:3323) (3323-3347) | Cập nhật tổng account statuses/tasks/footer. |
| [`MainToolApp.change_batch`](E:/FacebookTool_Project/client_app.py:3349) (3349-3354) | Đi tới batch trước/sau trong phạm vi. |
| [`MainToolApp.show_batch`](E:/FacebookTool_Project/client_app.py:3356) (3356-3358) | Chọn batch và làm mới bảng/nhãn. |
| [`MainToolApp.on_account_state_selected`](E:/FacebookTool_Project/client_app.py:3360) (3360-3368) | Chọn account làm nguồn log đang hiển thị. |
| [`MainToolApp.show_global_log`](E:/FacebookTool_Project/client_app.py:3370) (3370-3376) | Chuyển nhật ký sang log tổng. |
| [`MainToolApp.render_log_view`](E:/FacebookTool_Project/client_app.py:3378) (3378-3397) | Render log của account chọn hoặc global log. |
| [`MainToolApp.set_account_state`](E:/FacebookTool_Project/client_app.py:3399) (3399-3401) | Update store rồi queue refresh UI. |
| [`MainToolApp.record_task_result`](E:/FacebookTool_Project/client_app.py:3403) (3403-3405) | Update task account rồi queue UI. |
| [`MainToolApp.finalize_active_account_tasks`](E:/FacebookTool_Project/client_app.py:3407) (3407-3409) | Finalize task chưa kết thúc theo lý do dừng/lỗi. |
| [`MainToolApp.resolve_effective_proxy [async]`](E:/FacebookTool_Project/client_app.py:3411) (3411-3439) | Giữ/resolved proxy riêng của account và đồng bộ UI/state. |
| [`MainToolApp.resolve_effective_proxy.update_proxy`](E:/FacebookTool_Project/client_app.py:3432) (3432-3437) | Callback UI ghi endpoint vào đúng row. |
| [`MainToolApp.stop_checkpoint_account`](E:/FacebookTool_Project/client_app.py:3441) (3441-3459) | Latch CHECKPOINT, ghi account list/lý do và ngắt account. |
| [`MainToolApp.guard_facebook_checkpoint [async]`](E:/FacebookTool_Project/client_app.py:3461) (3461-3469) | Kiểm dấu hiệu bị chặn và raise khi phải dừng account. |
| [`MainToolApp.watch_facebook_checkpoint [async]`](E:/FacebookTool_Project/client_app.py:3471) (3471-3485) | Poll account/page state tới khi dừng hoặc tài nguyên đóng. |
| [`MainToolApp.set_account_failure`](E:/FacebookTool_Project/client_app.py:3487) (3487-3498) | Map failure category, ghi status/log và cập nhật UI. |
| [`MainToolApp.reset_create_page_account_results`](E:/FacebookTool_Project/client_app.py:3500) (3500-3503) | Xóa phân nhóm kết quả RAM cho lần chạy mới. |
| [`MainToolApp.record_create_page_account_result`](E:/FacebookTool_Project/client_app.py:3505) (3505-3534) | Ghi completed/die/checkpoint cho account hiện tại. |
| [`MainToolApp.get_create_page_account_results`](E:/FacebookTool_Project/client_app.py:3536) (3536-3541) | Snapshot một nhóm kết quả dưới lock. |
| [`MainToolApp.get_processed_create_page_sources`](E:/FacebookTool_Project/client_app.py:3543) (3543-3549) | Lấy raw_line của completed/die, không gồm checkpoint. |
| [`MainToolApp.get_targets_for_mode`](E:/FacebookTool_Project/client_app.py:3551) (3551-3554) | Lọc target theo prefix mode, vẫn hỗ trợ danh sách cũ không có prefix. |
| [`MainToolApp.update_tree_row`](E:/FacebookTool_Project/client_app.py:3556) (3556-3579) | Callback cập nhật các cột bảng quản lý qua UI queue. |
| [`MainToolApp.update_tree_row._update`](E:/FacebookTool_Project/client_app.py:3558) (3558-3578) | Thực hiện đổi row values/màu nếu row còn tồn tại. |
| [`MainToolApp.log`](E:/FacebookTool_Project/client_app.py:3581) (3581-3605) | Route log vào đúng tài khoản hiện tại hoặc nhật ký tổng. |
| [`MainToolApp.take_error_snapshot [async]`](E:/FacebookTool_Project/client_app.py:3608) (3608-3634) | Chụp ảnh màn hình toàn trang khi có lỗi để phục vụ quá trình debug. |
| [`MainToolApp.open_import_dialog`](E:/FacebookTool_Project/client_app.py:3636) (3636-3637) | Mở ImportAccountDialog. |
| [`MainToolApp.add_accounts_to_table`](E:/FacebookTool_Project/client_app.py:3639) (3639-3660) | Ghép input mới, đánh STT và reload/save bảng. |
| [`MainToolApp.delete_selected_rows`](E:/FacebookTool_Project/client_app.py:3662) (3662-3696) | Xóa dòng chọn và dựng lại input/bảng/state. |
| [`MainToolApp.save_settings`](E:/FacebookTool_Project/client_app.py:3700) (3700-3736) | Đọc UI, bảo vệ field nhạy cảm và ghi JSON. |
| [`MainToolApp.load_settings`](E:/FacebookTool_Project/client_app.py:3738) (3738-3790) | Nạp JSON, restore widget/options/theme/account. |
| [`MainToolApp.on_close`](E:/FacebookTool_Project/client_app.py:3794) (3794-3818) | Save, yêu cầu Stop rồi chờ hữu hạn trước destroy root. |
| [`MainToolApp.on_close.wait_for_worker`](E:/FacebookTool_Project/client_app.py:3807) (3807-3812) | Poll thread và deadline để quyết định đóng cửa sổ. |
| [`MainToolApp.import_accounts_file`](E:/FacebookTool_Project/client_app.py:3820) (3820-3832) | Đọc text account từ file, chuẩn hóa số thứ tự rồi refresh. |
| [`MainToolApp.import_proxies_file`](E:/FacebookTool_Project/client_app.py:3834) (3834-3842) | Đọc file proxy và refresh lựa chọn/proxy count. |
| [`MainToolApp.export_to_csv`](E:/FacebookTool_Project/client_app.py:3844) (3844-3859) | Xuất schema quản lý có password/2FA ra CSV. |
| [`MainToolApp.reload_table_from_text`](E:/FacebookTool_Project/client_app.py:3860) (3860-3943) | Parse input/preview proxy/sync state; return ngay nếu is_running. |
| [`MainToolApp.start_thread`](E:/FacebookTool_Project/client_app.py:3945) (3945-3990) | Snapshot cấu hình, đổi nút và launch run thread; hiện đặt running trước reload. |
| [`MainToolApp.stop_bot`](E:/FacebookTool_Project/client_app.py:3992) (3992-4005) | Đặt stop flags, queue UI đang dừng và schedule task cancellation. |
| [`MainToolApp.stop_bot.mark_stopping`](E:/FacebookTool_Project/client_app.py:3998) (3998-4001) | Callback vô hiệu nút Stop và đổi nhãn trạng thái. |
| [`MainToolApp._cancel_worker_tasks`](E:/FacebookTool_Project/client_app.py:4007) (4007-4010) | Cancel mọi worker task chưa done. |
| [`MainToolApp.finish_run`](E:/FacebookTool_Project/client_app.py:4012) (4012-4033) | Chờ thread chết, reset pointers/nút và hiển thị kết quả top-level. |
| [`MainToolApp.run_process`](E:/FacebookTool_Project/client_app.py:4035) (4035-4052) | Khởi tạo vòng lặp sự kiện tương thích tuyệt đối với Windows và Playwright |
| [`MainToolApp.run_change_password [async]`](E:/FacebookTool_Project/client_app.py:4055) (4055-4089) | Tự động đổi mật khẩu tài khoản qua giao diện Accounts Center |
| [`MainToolApp.run_enable_2fa [async]`](E:/FacebookTool_Project/client_app.py:4091) (4091-4173) | Tự động truy cập bật xác thực 2 yếu tố (2FA) và lấy Secret Key |
| [`MainToolApp.run_logout_other_sessions [async]`](E:/FacebookTool_Project/client_app.py:4175) (4175-4201) | Tự động đăng xuất tất cả các thiết bị/phiên đăng nhập khác |
| [`MainToolApp.run_add_page_admin [async]`](E:/FacebookTool_Project/client_app.py:4202) (4202-4350) | Cấp quyền với Page/account target binding và kiểm feedback. |
| [`MainToolApp.run_add_page_admin.finish`](E:/FacebookTool_Project/client_app.py:4205) (4205-4218) | Chuẩn hóa outcome, ghi task/log/file cấp quyền. |
| [`MainToolApp.run_update_page_info [async]`](E:/FacebookTool_Project/client_app.py:4352) (4352-4383) | Tự động đổi tên Fanpage theo yêu cầu |
| [`MainToolApp.run_invite_friends_like_page [async]`](E:/FacebookTool_Project/client_app.py:4385) (4385-4420) | Mời toàn bộ danh sách bạn bè thích Fanpage |
| [`MainToolApp.run_inbox_post_commenters [async]`](E:/FacebookTool_Project/client_app.py:4422) (4422-4461) | Tự động quét người bình luận trên bài viết và gửi tin nhắn trực tiếp |
| [`MainToolApp.run_post_joined_groups [async]`](E:/FacebookTool_Project/client_app.py:4463) (4463-4507) | Tự động đăng bài lên các nhóm mà nick đã tham gia |
| [`MainToolApp.run_comment_with_image [async]`](E:/FacebookTool_Project/client_app.py:4509) (4509-4548) | Bình luận kèm hình ảnh sản phẩm vào bài viết |
| [`MainToolApp.run_scrape_group_members [async]`](E:/FacebookTool_Project/client_app.py:4550) (4550-4586) | Quét danh sách thành viên trong nhóm và xuất ra file group_members.txt |
| [`MainToolApp.run_scrape_contact_info [async]`](E:/FacebookTool_Project/client_app.py:4588) (4588-4618) | Quét Số điện thoại & Email hiển thị công khai trên phần giới thiệu Profile |
| [`MainToolApp.run_reg_facebook_hotmail [async]`](E:/FacebookTool_Project/client_app.py:4621) (4621-4676) | Tự động đăng ký tài khoản Facebook bằng Hotmail/Outlook kèm Proxy |
| [`MainToolApp.run_reg_tiktok [async]`](E:/FacebookTool_Project/client_app.py:4678) (4678-4708) | Tự động đăng ký nick TikTok bằng Email |
| [`MainToolApp.run_reg_instagram [async]`](E:/FacebookTool_Project/client_app.py:4710) (4710-4745) | Tự động đăng ký tài khoản Instagram qua Email |
| [`MainToolApp.login_facebook_user_pass [async]`](E:/FacebookTool_Project/client_app.py:4749) (4749-4796) | Đăng nhập Facebook bằng tài khoản và mật khẩu đã được parse. |
| [`MainToolApp.login_tiktok_user_pass [async]`](E:/FacebookTool_Project/client_app.py:4798) (4798-4832) | Tự động đăng nhập TikTok bằng Username/Email và Password |
| [`MainToolApp.run_tiktok_keyword_follow_comment [async]`](E:/FacebookTool_Project/client_app.py:4834) (4834-4916) | Tự động tìm kiếm video TikTok: Xử lý popup -> Xem video -> Follow -> Thả tim -> Like Top Comment -> Bình luận |
| [`MainToolApp.warm_up_feed [async]`](E:/FacebookTool_Project/client_app.py:4918) (4918-4978) | Lướt Newfeed kết hợp Health Check, Soft Timeout và Telemetry Metrics |
| [`MainToolApp.create_browser_page [async]`](E:/FacebookTool_Project/client_app.py:4980) (4980-5112) | Khởi tạo Browser + Context + Page. |
| [`MainToolApp.wait_between_page_jobs [async]`](E:/FacebookTool_Project/client_app.py:5114) (5114-5179) | Browse without reactions during the one configured inter-Page delay. |
| [`MainToolApp.wait_between_page_jobs.update_countdown`](E:/FacebookTool_Project/client_app.py:5124) (5124-5127) | Cập nhật remaining/next time và tác vụ hiện tại của account. |
| [`MainToolApp.wait_between_page_jobs.countdown [async]`](E:/FacebookTool_Project/client_app.py:5129) (5129-5135) | Timer async dựa deadline, check dừng và cập nhật định kỳ. |
| [`MainToolApp.human_surf_feed [async]`](E:/FacebookTool_Project/client_app.py:5181) (5181-5222) | Lướt Bảng tin như người thật trong khoảng thời gian chỉ định |
| [`MainToolApp.human_watch_movie_reviews [async]`](E:/FacebookTool_Project/client_app.py:5224) (5224-5244) | Mở Facebook Watch tìm và xem Review Phim trong khoảng thời gian chỉ định |
| [`MainToolApp.browse_external_web [async]`](E:/FacebookTool_Project/client_app.py:5245) (5245-5255) | Lướt báo/web ngoài tạo lịch sử tự nhiên |
| [`MainToolApp.watch_facebook_reels [async]`](E:/FacebookTool_Project/client_app.py:5257) (5257-5290) | Xem và lướt Video Reels Facebook tự động như người thật |
| [`MainToolApp.view_facebook_stories [async]`](E:/FacebookTool_Project/client_app.py:5292) (5292-5299) | Xem Story Facebook bạn bè |
| [`MainToolApp.check_notifications [async]`](E:/FacebookTool_Project/client_app.py:5301) (5301-5310) | Mở xem thông báo |
| [`MainToolApp.react_messenger [async]`](E:/FacebookTool_Project/client_app.py:5312) (5312-5321) | Thả cảm xúc Messenger |
| [`MainToolApp.interact_fanpage [async]`](E:/FacebookTool_Project/client_app.py:5323) (5323-5329) | Tương tác Fanpage |
| [`MainToolApp.cancel_old_requests [async]`](E:/FacebookTool_Project/client_app.py:5331) (5331-5338) | Hủy các lời mời kết bạn gửi đi đã quá lâu |
| [`MainToolApp.get_current_friends_count [async]`](E:/FacebookTool_Project/client_app.py:5340) (5340-5351) | Lấy số lượng bạn bè hiện tại |
| [`MainToolApp.run_add_by_name [async]`](E:/FacebookTool_Project/client_app.py:5353) (5353-5463) | Tìm người theo tên/từ khóa rồi gửi lời mời kết bạn. |
| [`MainToolApp.click_and_confirm_friend_request [async]`](E:/FacebookTool_Project/client_app.py:5465) (5465-5523) | Bind evidence to the recipient's action group, never the whole page. |
| [`MainToolApp.record_friend_outcome`](E:/FacebookTool_Project/client_app.py:5525) (5525-5529) | Map outcome lời mời sang result task và log đúng account. |
| [`MainToolApp.verify_facebook_session [async]`](E:/FacebookTool_Project/client_app.py:5531) (5531-5555) | Loại URL/input invalid và yêu cầu c_user; hiện chưa có positive DOM proof. |
| [`MainToolApp.get_current_page_identity [async]`](E:/FacebookTool_Project/client_app.py:5557) (5557-5566) | Thu URL/ID/name/canonical evidence của Page qua browser. |
| [`MainToolApp.verify_created_page [async]`](E:/FacebookTool_Project/client_app.py:5568) (5568-5572) | Đối chiếu identity thu được với context job/owner đã submit. |
| [`MainToolApp.page_setup_transition_detected [async]`](E:/FacebookTool_Project/client_app.py:5574) (5574-5578) | Nhận diện chuyển sang onboarding, không tự xác nhận SUCCESS. |
| [`MainToolApp.get_page_setup_button [async]`](E:/FacebookTool_Project/client_app.py:5580) (5580-5592) | Tìm nút Next/Done/Skip trong flow thiết lập bằng selector/fallback. |
| [`MainToolApp.click_page_blank_margin [async]`](E:/FacebookTool_Project/client_app.py:5594) (5594-5609) | Click vùng trống an toàn ngoài input/control/dialog nếu tìm được. |
| [`MainToolApp.select_page_category [async]`](E:/FacebookTool_Project/client_app.py:5611) (5611-5646) | Chọn suggestion đúng category/alias và kiểm chip selection. |
| [`MainToolApp.ensure_personal_profile [async]`](E:/FacebookTool_Project/client_app.py:5647) (5647-5708) | Chuyển đổi danh tính từ Fanpage về lại tài khoản cá nhân trên giao diện. |
| [`MainToolApp.get_system_notifications [async]`](E:/FacebookTool_Project/client_app.py:5710) (5710-5724) | Tự động đọc mọi thông báo nổi, toast, alert hệ thống theo chuẩn ARIA. |
| [`MainToolApp.dismiss_floating_overlays [async]`](E:/FacebookTool_Project/client_app.py:5726) (5726-5740) | Tự động đóng mọi popup, toast, dialog nổi cản trở trên màn hình. |
| [`MainToolApp.human_type [async]`](E:/FacebookTool_Project/client_app.py:5741) (5741-5754) | Gõ từng ký tự với độ trễ biến thiên, mô phỏng gõ nhầm và sửa lại. |
| [`MainToolApp.human_click [async]`](E:/FacebookTool_Project/client_app.py:5756) (5756-5768) | Di chuyển chuột có quỹ đạo mềm và click lệch tâm tự nhiên. |
| [`MainToolApp.safe_action_click [async]`](E:/FacebookTool_Project/client_app.py:5769) (5769-5800) | Click an toàn khi DOM thay đổi, tự động retry khi bị Stale Element. |
| [`MainToolApp.run_create_page [async]`](E:/FacebookTool_Project/client_app.py:5801) (5801-6434) | Tạo Fanpage: Tích hợp check Checkpoint, đa tầng Selector, xử lý Stale Element (DOM refresh), |
| [`MainToolApp.run_create_page.record_result`](E:/FacebookTool_Project/client_app.py:5822) (5822-5849) | Chuẩn hóa result job, ghi outcome và cập nhật task/count theo nhánh. |
| [`MainToolApp.run_create_page.set_page_flow_state`](E:/FacebookTool_Project/client_app.py:5893) (5893-5899) | Update Page context và action/log tương ứng. |
| [`MainToolApp.run_create_page.navigate_to_creation [async]`](E:/FacebookTool_Project/client_app.py:5917) (5917-5924) | Guard và goto creation trong nhánh được retry trước submit. |
| [`MainToolApp.run_add_by_group [async]`](E:/FacebookTool_Project/client_app.py:6436) (6436-6468) | Kết bạn theo danh sách thành viên nhóm |
| [`MainToolApp.run_add_by_uid [async]`](E:/FacebookTool_Project/client_app.py:6470) (6470-6511) | Kết bạn theo danh sách UID / Link Profile |
| [`MainToolApp.run_join_groups [async]`](E:/FacebookTool_Project/client_app.py:6513) (6513-6528) | Tham gia nhóm theo Link hoặc ID |
| [`MainToolApp.run_auto_post [async]`](E:/FacebookTool_Project/client_app.py:6530) (6530-6554) | Tự động đăng bài lên tường cá nhân |
| [`MainToolApp.run_auto_inbox [async]`](E:/FacebookTool_Project/client_app.py:6556) (6556-6579) | Tự động gửi tin nhắn cho danh sách UID |
| [`MainToolApp.run_seed_group [async]`](E:/FacebookTool_Project/client_app.py:6581) (6581-6601) | Seeding tương tác bài viết trong nhóm |
| [`MainToolApp.run_change_bio [async]`](E:/FacebookTool_Project/client_app.py:6602) (6602-6621) | Cập nhật tiểu sử Bio |
| [`MainToolApp.run_change_avatar [async]`](E:/FacebookTool_Project/client_app.py:6623) (6623-6644) | Cập nhật ảnh đại diện từ file đường dẫn |
| [`MainToolApp.run_invite_friends_to_group [async]`](E:/FacebookTool_Project/client_app.py:6646) (6646-6668) | Mời bạn bè vào nhóm |
| [`MainToolApp.run_scrape_uid_post [async]`](E:/FacebookTool_Project/client_app.py:6670) (6670-6686) | Quét UID tương tác bài viết |
| [`MainToolApp.run_post_page [async]`](E:/FacebookTool_Project/client_app.py:6688) (6688-6709) | Đăng bài lên Fanpage |
| [`MainToolApp.run_seed_live [async]`](E:/FacebookTool_Project/client_app.py:6711) (6711-6728) | Bão Seeding Livestream Facebook |
| [`MainToolApp.process_account_scoped [async]`](E:/FacebookTool_Project/client_app.py:6730) (6730-6736) | Set/reset ContextVar để các log async thuộc đúng account. |
| [`MainToolApp.process_account [async]`](E:/FacebookTool_Project/client_app.py:6738) (6738-7138) | Browser/session/tác vụ/finalize/cleanup riêng cho account dưới semaphore. |
| [`MainToolApp.parse_range_string`](E:/FacebookTool_Project/client_app.py:7139) (7139-7153) | Tự động phân tách chuỗi số phức hợp dạng '1, 3, 5-9' thành danh sách STT |
| [`MainToolApp.main_worker [async]`](E:/FacebookTool_Project/client_app.py:7156) (7156-7335) | Dựng jobs/kế hoạch/batches, chạy async tasks và tổng kết. |
| [`MainToolApp.check_live_selected`](E:/FacebookTool_Project/client_app.py:7337) (7337-7384) | Kiểm UID qua Graph picture; UNKNOWN hoặc ERROR, không chứng minh login LIVE. |
| [`MainToolApp.check_live_selected.worker`](E:/FacebookTool_Project/client_app.py:7352) (7352-7382) | Thread HTTP UID check và queue result UI. |
| [`MainToolApp.get_parsed_account_for_item`](E:/FacebookTool_Project/client_app.py:7386) (7386-7399) | Parse lại dòng textbox tương ứng item để dùng tiện ích thủ công. |
| [`MainToolApp.open_selected_profile`](E:/FacebookTool_Project/client_app.py:7402) (7402-7463) | Mở persistent profile riêng cho account chọn. |
| [`MainToolApp.open_selected_profile.launch`](E:/FacebookTool_Project/client_app.py:7422) (7422-7461) | Entry thread khởi chạy async tiện ích profile. |
| [`MainToolApp.open_selected_profile.launch.run [async]`](E:/FacebookTool_Project/client_app.py:7431) (7431-7460) | Tạo persistent browser, add cookie, giữ cửa sổ và close khi kết thúc. |
| [`MainToolApp.get_token_selected`](E:/FacebookTool_Project/client_app.py:7466) (7466-7509) | Trích xuất Access Token EAAB từ Cookie tài khoản |
| [`MainToolApp.get_token_selected.extract_worker`](E:/FacebookTool_Project/client_app.py:7484) (7484-7507) | Thread request cookie để tìm token từ trang liên quan. |
| [`MainToolApp.get_token_selected.extract_worker.show_success`](E:/FacebookTool_Project/client_app.py:7499) (7499-7502) | Hiển thị token đã lấy/copy theo UI; chứa thông tin nhạy cảm. |
| [`MainToolApp.generate_2fa_dialog`](E:/FacebookTool_Project/client_app.py:7511) (7511-7537) | Tạo mã xác thực 2FA 6 số nhanh từ 2FA Private Key |
| [`main`](E:/FacebookTool_Project/client_app.py:7539) (7539-7560) | Đọc/verify license và tạo vòng lặp app hoặc cửa sổ kích hoạt. |
| [`main.launch_main`](E:/FacebookTool_Project/client_app.py:7550) (7550-7557) | Đóng root kích hoạt rồi tạo root ứng dụng chính. |

### account_history.py

132 dòng source; 7 khai báo hàm/callback, 1 class. Đây không phải số test cases.

| Class / vị trí | Vai trò |
|---|---|
| [`AccountHistoryStore`](E:/FacebookTool_Project/account_history.py:60) (60-132) | SQLite history store. |

| Hàm / vị trí | Trách nhiệm hoặc mục tiêu kiểm thử |
|---|---|
| [`history_account_id`](E:/FacebookTool_Project/account_history.py:12) (12-16) | Chọn khóa lịch sử ổn định, hash nếu định danh có dấu hiệu chứa credentials. |
| [`safe_proxy_label`](E:/FacebookTool_Project/account_history.py:19) (19-33) | Bỏ auth khỏi proxy để lưu endpoint an toàn hơn. |
| [`redact_history_text`](E:/FacebookTool_Project/account_history.py:36) (36-57) | Che raw/password/2FA/cookie/token và proxy auth trong nội dung lịch sử. |
| [`AccountHistoryStore.__init__`](E:/FacebookTool_Project/account_history.py:61) (61-78) | Tạo thư mục, SQLite tables/index và RLock. |
| [`AccountHistoryStore.save`](E:/FacebookTool_Project/account_history.py:80) (80-121) | Redact snapshot, upsert account và ghi event khác event liền trước. |
| [`AccountHistoryStore.save.sanitize`](E:/FacebookTool_Project/account_history.py:87) (87-93) | Duyệt tasks đệ quy, bỏ credential keys và redact chuỗi. |
| [`AccountHistoryStore.load`](E:/FacebookTool_Project/account_history.py:123) (123-132) | Đọc snapshot và tối đa 500 event gần nhất của account. |

### admin_key_gen.py

7 dòng source; 0 khai báo hàm/callback, 0 class. Đây không phải số test cases.

Không khai báo hàm: các câu lệnh top-level thực hiện trách nhiệm đã mô tả ở bản đồ project.

### tests/test_core.py

1881 dòng source; 171 khai báo hàm/callback, 22 class. Đây không phải số test cases.

| Class / vị trí | Vai trò |
|---|---|
| [`CoreHelpersTest`](E:/FacebookTool_Project/tests/test_core.py:15) (15-1235) | Nhóm regression tests; không chạy Facebook production. |
| [`CoreHelpersTest.test_update_url_must_be_trusted_executable.FakeResponse`](E:/FacebookTool_Project/tests/test_core.py:92) (92-102) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_cookie_parser_preserves_values.FakeText`](E:/FacebookTool_Project/tests/test_core.py:123) (123-134) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator`](E:/FacebookTool_Project/tests/test_core.py:328) (328-348) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakePage`](E:/FacebookTool_Project/tests/test_core.py:350) (350-369) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeContext`](E:/FacebookTool_Project/tests/test_core.py:371) (371-379) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeBrowser`](E:/FacebookTool_Project/tests/test_core.py:381) (381-383) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton`](E:/FacebookTool_Project/tests/test_core.py:468) (468-503) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.EmptyLocator`](E:/FacebookTool_Project/tests/test_core.py:505) (505-511) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendPage`](E:/FacebookTool_Project/tests/test_core.py:513) (513-516) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_page_admin_job_is_scoped_to_account.TargetLocator`](E:/FacebookTool_Project/tests/test_core.py:739) (739-744) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeKeyboard`](E:/FacebookTool_Project/tests/test_core.py:776) (776-788) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator`](E:/FacebookTool_Project/tests/test_core.py:790) (790-853) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse`](E:/FacebookTool_Project/tests/test_core.py:855) (855-872) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage`](E:/FacebookTool_Project/tests/test_core.py:874) (874-968) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.Closable`](E:/FacebookTool_Project/tests/test_core.py:1201) (1201-1206) | Class mô phỏng browser/locator/resource bên trong test tương ứng. |
| [`UpdateRestartRegressionTests`](E:/FacebookTool_Project/tests/test_core.py:1238) (1238-1301) | Nhóm regression tests; không chạy Facebook production. |
| [`CheckpointRuntimeTests`](E:/FacebookTool_Project/tests/test_core.py:1304) (1304-1499) | Nhóm regression tests; không chạy Facebook production. |
| [`RunLifecycleTests`](E:/FacebookTool_Project/tests/test_core.py:1502) (1502-1643) | Nhóm regression tests; không chạy Facebook production. |
| [`PageSetupRuntimeTests`](E:/FacebookTool_Project/tests/test_core.py:1646) (1646-1705) | Nhóm regression tests; không chạy Facebook production. |
| [`PageMarginClickTests`](E:/FacebookTool_Project/tests/test_core.py:1708) (1708-1769) | Nhóm regression tests; không chạy Facebook production. |
| [`PageWaitTests`](E:/FacebookTool_Project/tests/test_core.py:1772) (1772-1877) | Nhóm regression tests; không chạy Facebook production. |

| Hàm / vị trí | Trách nhiệm hoặc mục tiêu kiểm thử |
|---|---|
| [`CoreHelpersTest.test_cookie_login_accepts_supported_import_formats`](E:/FacebookTool_Project/tests/test_core.py:16) (16-36) | Case kiểm thử: cookie login accepts supported import formats. |
| [`CoreHelpersTest.test_cookie_detection_does_not_match_password_substrings`](E:/FacebookTool_Project/tests/test_core.py:38) (38-41) | Case kiểm thử: cookie detection does not match password substrings. |
| [`CoreHelpersTest.test_version_comparison_is_numeric`](E:/FacebookTool_Project/tests/test_core.py:43) (43-44) | Case kiểm thử: version comparison is numeric. |
| [`CoreHelpersTest.test_update_url_must_be_trusted_executable`](E:/FacebookTool_Project/tests/test_core.py:46) (46-116) | Case kiểm thử: update url must be trusted executable. |
| [`CoreHelpersTest.test_update_url_must_be_trusted_executable.FakeResponse.__enter__`](E:/FacebookTool_Project/tests/test_core.py:95) (95-96) | Helper/mô phỏng phục vụ case test_update_url_must_be_trusted_executable; không phải production flow. |
| [`CoreHelpersTest.test_update_url_must_be_trusted_executable.FakeResponse.__exit__`](E:/FacebookTool_Project/tests/test_core.py:98) (98-99) | Helper/mô phỏng phục vụ case test_update_url_must_be_trusted_executable; không phải production flow. |
| [`CoreHelpersTest.test_update_url_must_be_trusted_executable.FakeResponse.read`](E:/FacebookTool_Project/tests/test_core.py:101) (101-102) | Helper/mô phỏng phục vụ case test_update_url_must_be_trusted_executable; không phải production flow. |
| [`CoreHelpersTest.test_cookie_parser_preserves_values`](E:/FacebookTool_Project/tests/test_core.py:118) (118-177) | Case kiểm thử: cookie parser preserves values. |
| [`CoreHelpersTest.test_cookie_parser_preserves_values.FakeText.__init__`](E:/FacebookTool_Project/tests/test_core.py:124) (124-125) | Helper/mô phỏng phục vụ case test_cookie_parser_preserves_values; không phải production flow. |
| [`CoreHelpersTest.test_cookie_parser_preserves_values.FakeText.get`](E:/FacebookTool_Project/tests/test_core.py:127) (127-128) | Helper/mô phỏng phục vụ case test_cookie_parser_preserves_values; không phải production flow. |
| [`CoreHelpersTest.test_cookie_parser_preserves_values.FakeText.delete`](E:/FacebookTool_Project/tests/test_core.py:130) (130-131) | Helper/mô phỏng phục vụ case test_cookie_parser_preserves_values; không phải production flow. |
| [`CoreHelpersTest.test_cookie_parser_preserves_values.FakeText.insert`](E:/FacebookTool_Project/tests/test_core.py:133) (133-134) | Helper/mô phỏng phục vụ case test_cookie_parser_preserves_values; không phải production flow. |
| [`CoreHelpersTest.test_proxy_parser_supports_authenticated_and_scheme_formats`](E:/FacebookTool_Project/tests/test_core.py:179) (179-203) | Case kiểm thử: proxy parser supports authenticated and scheme formats. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches`](E:/FacebookTool_Project/tests/test_core.py:205) (205-523) | Case kiểm thử: account state isolation failures and batches. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.update_scoped_account [async]`](E:/FacebookTool_Project/tests/test_core.py:301) (301-304) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.update_both_accounts [async]`](E:/FacebookTool_Project/tests/test_core.py:306) (306-310) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator.__init__`](E:/FacebookTool_Project/tests/test_core.py:329) (329-331) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator.first`](E:/FacebookTool_Project/tests/test_core.py:334) (334-335) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator.fill [async]`](E:/FacebookTool_Project/tests/test_core.py:337) (337-338) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator.count [async]`](E:/FacebookTool_Project/tests/test_core.py:340) (340-341) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator.click [async]`](E:/FacebookTool_Project/tests/test_core.py:343) (343-345) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeLocator.is_visible [async]`](E:/FacebookTool_Project/tests/test_core.py:347) (347-348) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakePage.__init__`](E:/FacebookTool_Project/tests/test_core.py:351) (351-354) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakePage.goto [async]`](E:/FacebookTool_Project/tests/test_core.py:356) (356-359) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakePage.locator`](E:/FacebookTool_Project/tests/test_core.py:361) (361-366) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakePage.wait_for_timeout [async]`](E:/FacebookTool_Project/tests/test_core.py:368) (368-369) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeContext.add_cookies [async]`](E:/FacebookTool_Project/tests/test_core.py:372) (372-373) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeContext.cookies [async]`](E:/FacebookTool_Project/tests/test_core.py:375) (375-376) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeContext.close [async]`](E:/FacebookTool_Project/tests/test_core.py:378) (378-379) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FakeBrowser.close [async]`](E:/FacebookTool_Project/tests/test_core.py:382) (382-383) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.run_login_case [async]`](E:/FacebookTool_Project/tests/test_core.py:385) (385-441) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.run_login_case.create_browser_page [async]`](E:/FacebookTool_Project/tests/test_core.py:418) (418-419) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.run_login_case.get_current_friends_count [async]`](E:/FacebookTool_Project/tests/test_core.py:421) (421-422) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.__init__`](E:/FacebookTool_Project/tests/test_core.py:469) (469-470) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.get_attribute [async]`](E:/FacebookTool_Project/tests/test_core.py:472) (472-477) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.inner_text [async]`](E:/FacebookTool_Project/tests/test_core.py:479) (479-480) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.click [async]`](E:/FacebookTool_Project/tests/test_core.py:482) (482-483) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.count [async]`](E:/FacebookTool_Project/tests/test_core.py:485) (485-486) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.is_visible [async]`](E:/FacebookTool_Project/tests/test_core.py:488) (488-489) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.evaluate_handle [async]`](E:/FacebookTool_Project/tests/test_core.py:491) (491-492) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.as_element`](E:/FacebookTool_Project/tests/test_core.py:494) (494-495) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.evaluate [async]`](E:/FacebookTool_Project/tests/test_core.py:497) (497-500) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendButton.dispose [async]`](E:/FacebookTool_Project/tests/test_core.py:502) (502-503) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.EmptyLocator.last`](E:/FacebookTool_Project/tests/test_core.py:507) (507-508) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.EmptyLocator.count [async]`](E:/FacebookTool_Project/tests/test_core.py:510) (510-511) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_account_state_isolation_failures_and_batches.FriendPage.locator`](E:/FacebookTool_Project/tests/test_core.py:515) (515-516) | Helper/mô phỏng phục vụ case test_account_state_isolation_failures_and_batches; không phải production flow. |
| [`CoreHelpersTest.test_create_page_button_languages`](E:/FacebookTool_Project/tests/test_core.py:525) (525-530) | Case kiểm thử: create page button languages. |
| [`CoreHelpersTest.test_page_plan_supports_name_and_category`](E:/FacebookTool_Project/tests/test_core.py:532) (532-578) | Case kiểm thử: page plan supports name and category. |
| [`CoreHelpersTest.test_page_context_requires_verified_identity_for_success`](E:/FacebookTool_Project/tests/test_core.py:580) (580-597) | Case kiểm thử: page context requires verified identity for success. |
| [`CoreHelpersTest.test_page_count_semantics_one_five_and_fifteen`](E:/FacebookTool_Project/tests/test_core.py:599) (599-604) | Case kiểm thử: page count semantics one five and fifteen. |
| [`CoreHelpersTest.test_page_access_feedback_is_not_false_success`](E:/FacebookTool_Project/tests/test_core.py:606) (606-610) | Case kiểm thử: page access feedback is not false success. |
| [`CoreHelpersTest.test_page_access_result_keeps_owner_page_and_target`](E:/FacebookTool_Project/tests/test_core.py:612) (612-619) | Case kiểm thử: page access result keeps owner page and target. |
| [`CoreHelpersTest.test_page_and_access_worker_limits`](E:/FacebookTool_Project/tests/test_core.py:621) (621-633) | Case kiểm thử: page and access worker limits. |
| [`CoreHelpersTest.test_page_duplicate_keys_use_verified_identity`](E:/FacebookTool_Project/tests/test_core.py:635) (635-643) | Case kiểm thử: page duplicate keys use verified identity. |
| [`CoreHelpersTest.test_page_url_without_numeric_id_is_verified`](E:/FacebookTool_Project/tests/test_core.py:645) (645-650) | Case kiểm thử: page url without numeric id is verified. |
| [`CoreHelpersTest.test_page_missing_identity_cannot_be_success`](E:/FacebookTool_Project/tests/test_core.py:652) (652-656) | Case kiểm thử: page missing identity cannot be success. |
| [`CoreHelpersTest.test_create_page_transient_retry_uses_bounded_backoff`](E:/FacebookTool_Project/tests/test_core.py:658) (658-674) | Case kiểm thử: create page transient retry uses bounded backoff. |
| [`CoreHelpersTest.test_create_page_transient_retry_uses_bounded_backoff.operation [async]`](E:/FacebookTool_Project/tests/test_core.py:661) (661-665) | Helper/mô phỏng phục vụ case test_create_page_transient_retry_uses_bounded_backoff; không phải production flow. |
| [`CoreHelpersTest.test_create_page_permanent_error_is_not_retried`](E:/FacebookTool_Project/tests/test_core.py:676) (676-687) | Case kiểm thử: create page permanent error is not retried. |
| [`CoreHelpersTest.test_create_page_permanent_error_is_not_retried.operation [async]`](E:/FacebookTool_Project/tests/test_core.py:679) (679-681) | Helper/mô phỏng phục vụ case test_create_page_permanent_error_is_not_retried; không phải production flow. |
| [`CoreHelpersTest.test_create_page_network_errors_are_technical`](E:/FacebookTool_Project/tests/test_core.py:689) (689-693) | Case kiểm thử: create page network errors are technical. |
| [`CoreHelpersTest.test_parallel_page_contexts_do_not_cross_account`](E:/FacebookTool_Project/tests/test_core.py:695) (695-704) | Case kiểm thử: parallel page contexts do not cross account. |
| [`CoreHelpersTest.test_cancelled_page_context_is_never_verified`](E:/FacebookTool_Project/tests/test_core.py:706) (706-710) | Case kiểm thử: cancelled page context is never verified. |
| [`CoreHelpersTest.test_page_admin_mapping_rejects_other_owner`](E:/FacebookTool_Project/tests/test_core.py:712) (712-718) | Case kiểm thử: page admin mapping rejects other owner. |
| [`CoreHelpersTest.test_page_admin_job_is_scoped_to_account`](E:/FacebookTool_Project/tests/test_core.py:720) (720-751) | Case kiểm thử: page admin job is scoped to account. |
| [`CoreHelpersTest.test_page_admin_job_is_scoped_to_account.TargetLocator.get_attribute [async]`](E:/FacebookTool_Project/tests/test_core.py:740) (740-741) | Helper/mô phỏng phục vụ case test_page_admin_job_is_scoped_to_account; không phải production flow. |
| [`CoreHelpersTest.test_page_admin_job_is_scoped_to_account.TargetLocator.inner_text [async]`](E:/FacebookTool_Project/tests/test_core.py:743) (743-744) | Helper/mô phỏng phục vụ case test_page_admin_job_is_scoped_to_account; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen`](E:/FacebookTool_Project/tests/test_core.py:753) (753-1211) | Case kiểm thử: page identity rejects creation screen. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeKeyboard.__init__`](E:/FacebookTool_Project/tests/test_core.py:777) (777-778) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeKeyboard.press [async]`](E:/FacebookTool_Project/tests/test_core.py:780) (780-781) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeKeyboard.type [async]`](E:/FacebookTool_Project/tests/test_core.py:783) (783-788) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.__init__`](E:/FacebookTool_Project/tests/test_core.py:791) (791-800) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.first`](E:/FacebookTool_Project/tests/test_core.py:803) (803-804) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.nth`](E:/FacebookTool_Project/tests/test_core.py:806) (806-807) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.count [async]`](E:/FacebookTool_Project/tests/test_core.py:809) (809-810) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.is_visible [async]`](E:/FacebookTool_Project/tests/test_core.py:812) (812-813) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.is_enabled [async]`](E:/FacebookTool_Project/tests/test_core.py:815) (815-816) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.wait_for [async]`](E:/FacebookTool_Project/tests/test_core.py:818) (818-820) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.scroll_into_view_if_needed [async]`](E:/FacebookTool_Project/tests/test_core.py:822) (822-823) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.click [async]`](E:/FacebookTool_Project/tests/test_core.py:825) (825-829) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.focus [async]`](E:/FacebookTool_Project/tests/test_core.py:831) (831-834) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.fill [async]`](E:/FacebookTool_Project/tests/test_core.py:836) (836-839) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.get_attribute [async]`](E:/FacebookTool_Project/tests/test_core.py:841) (841-842) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.bounding_box [async]`](E:/FacebookTool_Project/tests/test_core.py:844) (844-847) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.inner_text [async]`](E:/FacebookTool_Project/tests/test_core.py:849) (849-850) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeLocator.evaluate [async]`](E:/FacebookTool_Project/tests/test_core.py:852) (852-853) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse.__init__`](E:/FacebookTool_Project/tests/test_core.py:856) (856-857) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse.click [async]`](E:/FacebookTool_Project/tests/test_core.py:859) (859-860) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse.move [async]`](E:/FacebookTool_Project/tests/test_core.py:862) (862-863) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse.down [async]`](E:/FacebookTool_Project/tests/test_core.py:865) (865-866) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse.up [async]`](E:/FacebookTool_Project/tests/test_core.py:868) (868-869) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakeMouse.wheel [async]`](E:/FacebookTool_Project/tests/test_core.py:871) (871-872) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.__init__`](E:/FacebookTool_Project/tests/test_core.py:875) (875-891) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.evaluate [async]`](E:/FacebookTool_Project/tests/test_core.py:893) (893-900) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.goto [async]`](E:/FacebookTool_Project/tests/test_core.py:902) (902-903) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.title [async]`](E:/FacebookTool_Project/tests/test_core.py:905) (905-906) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.inner_text [async]`](E:/FacebookTool_Project/tests/test_core.py:908) (908-909) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.locator`](E:/FacebookTool_Project/tests/test_core.py:911) (911-938) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.locator.focus_category`](E:/FacebookTool_Project/tests/test_core.py:921) (921-923) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.get_by_role`](E:/FacebookTool_Project/tests/test_core.py:940) (940-968) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.get_by_role.advance_setup`](E:/FacebookTool_Project/tests/test_core.py:948) (948-951) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.FakePage.get_by_role.finish_create`](E:/FacebookTool_Project/tests/test_core.py:955) (955-962) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.run_create_case [async]`](E:/FacebookTool_Project/tests/test_core.py:970) (970-1042) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.run_create_case.take_error_snapshot [async]`](E:/FacebookTool_Project/tests/test_core.py:1005) (1005-1006) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.run_create_case.ensure_personal_profile [async]`](E:/FacebookTool_Project/tests/test_core.py:1010) (1010-1011) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.transient_operation [async]`](E:/FacebookTool_Project/tests/test_core.py:1189) (1189-1193) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.Closable.__init__`](E:/FacebookTool_Project/tests/test_core.py:1202) (1202-1203) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_page_identity_rejects_creation_screen.Closable.close [async]`](E:/FacebookTool_Project/tests/test_core.py:1205) (1205-1206) | Helper/mô phỏng phục vụ case test_page_identity_rejects_creation_screen; không phải production flow. |
| [`CoreHelpersTest.test_async_methods_do_not_read_tk_widgets`](E:/FacebookTool_Project/tests/test_core.py:1213) (1213-1235) | Case kiểm thử: async methods do not read tk widgets. |
| [`UpdateRestartRegressionTests.test_restart_environment_resets_private_state_and_keeps_user_environment`](E:/FacebookTool_Project/tests/test_core.py:1239) (1239-1243) | Case kiểm thử: restart environment resets private state and keeps user environment. |
| [`UpdateRestartRegressionTests.test_interpreter_guards_are_preserved`](E:/FacebookTool_Project/tests/test_core.py:1245) (1245-1249) | Case kiểm thử: interpreter guards are preserved. |
| [`UpdateRestartRegressionTests.test_restart_failure_preserves_installed_executable`](E:/FacebookTool_Project/tests/test_core.py:1251) (1251-1270) | Case kiểm thử: restart failure preserves installed executable. |
| [`UpdateRestartRegressionTests.test_checkpoint_cancellation_never_retries_creation`](E:/FacebookTool_Project/tests/test_core.py:1272) (1272-1276) | Case kiểm thử: checkpoint cancellation never retries creation. |
| [`UpdateRestartRegressionTests.test_invalid_download_never_reaches_restart_or_replace`](E:/FacebookTool_Project/tests/test_core.py:1278) (1278-1301) | Case kiểm thử: invalid download never reaches restart or replace. |
| [`CheckpointRuntimeTests.setUp`](E:/FacebookTool_Project/tests/test_core.py:1305) (1305-1333) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`CheckpointRuntimeTests.resources`](E:/FacebookTool_Project/tests/test_core.py:1335) (1335-1350) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`CheckpointRuntimeTests.run_worker [async]`](E:/FacebookTool_Project/tests/test_core.py:1352) (1352-1357) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`CheckpointRuntimeTests.test_checkpoint_worker_stops_actions_and_closes_own_resources [async]`](E:/FacebookTool_Project/tests/test_core.py:1359) (1359-1376) | Case kiểm thử: checkpoint worker stops actions and closes own resources. |
| [`CheckpointRuntimeTests.test_checkpoint_worker_stops_actions_and_closes_own_resources.check_ui_queued_before_close [async]`](E:/FacebookTool_Project/tests/test_core.py:1361) (1361-1363) | Helper/mô phỏng phục vụ case test_checkpoint_worker_stops_actions_and_closes_own_resources; không phải production flow. |
| [`CheckpointRuntimeTests.test_challenge_is_checkpoint_and_external_urls_are_not [async]`](E:/FacebookTool_Project/tests/test_core.py:1378) (1378-1387) | Case kiểm thử: challenge is checkpoint and external urls are not. |
| [`CheckpointRuntimeTests.test_structural_checkpoint_form [async]`](E:/FacebookTool_Project/tests/test_core.py:1389) (1389-1392) | Case kiểm thử: structural checkpoint form. |
| [`CheckpointRuntimeTests.test_navigation_dom_replacement_is_not_false_error_or_checkpoint [async]`](E:/FacebookTool_Project/tests/test_core.py:1394) (1394-1399) | Case kiểm thử: navigation dom replacement is not false error or checkpoint. |
| [`CheckpointRuntimeTests.assert_checkpoint [async]`](E:/FacebookTool_Project/tests/test_core.py:1401) (1401-1404) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`CheckpointRuntimeTests.test_checkpoint_storage_deduplicates_and_preserves_raw_input [async]`](E:/FacebookTool_Project/tests/test_core.py:1406) (1406-1417) | Case kiểm thử: checkpoint storage deduplicates and preserves raw input. |
| [`CheckpointRuntimeTests.test_checkpoint_during_wait_cancels_without_manual_browser_close [async]`](E:/FacebookTool_Project/tests/test_core.py:1419) (1419-1437) | Case kiểm thử: checkpoint during wait cancels without manual browser close. |
| [`CheckpointRuntimeTests.test_checkpoint_during_wait_cancels_without_manual_browser_close.wait_action [async]`](E:/FacebookTool_Project/tests/test_core.py:1422) (1422-1424) | Helper/mô phỏng phục vụ case test_checkpoint_during_wait_cancels_without_manual_browser_close; không phải production flow. |
| [`CheckpointRuntimeTests.test_technical_errors_stay_error [async]`](E:/FacebookTool_Project/tests/test_core.py:1439) (1439-1446) | Case kiểm thử: technical errors stay error. |
| [`CheckpointRuntimeTests.test_invalid_proxy_stays_error [async]`](E:/FacebookTool_Project/tests/test_core.py:1448) (1448-1451) | Case kiểm thử: invalid proxy stays error. |
| [`CheckpointRuntimeTests.test_friend_error_does_not_become_completed_or_die [async]`](E:/FacebookTool_Project/tests/test_core.py:1453) (1453-1466) | Case kiểm thử: friend error does not become completed or die. |
| [`CheckpointRuntimeTests.test_empty_account_proxy_mode_allows_direct_browser [async]`](E:/FacebookTool_Project/tests/test_core.py:1468) (1468-1473) | Case kiểm thử: empty account proxy mode allows direct browser. |
| [`CheckpointRuntimeTests.test_cancelled_friend_worker_finalizes_running_task [async]`](E:/FacebookTool_Project/tests/test_core.py:1475) (1475-1493) | Case kiểm thử: cancelled friend worker finalizes running task. |
| [`CheckpointRuntimeTests.test_cancelled_friend_worker_finalizes_running_task.wait_action [async]`](E:/FacebookTool_Project/tests/test_core.py:1478) (1478-1480) | Helper/mô phỏng phục vụ case test_cancelled_friend_worker_finalizes_running_task; không phải production flow. |
| [`CheckpointRuntimeTests.test_policy_detection_is_not_a_technical_error [async]`](E:/FacebookTool_Project/tests/test_core.py:1495) (1495-1499) | Case kiểm thử: policy detection is not a technical error. |
| [`RunLifecycleTests.make_app`](E:/FacebookTool_Project/tests/test_core.py:1503) (1503-1519) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`RunLifecycleTests.test_ui_error_does_not_block_finish_or_future_callbacks`](E:/FacebookTool_Project/tests/test_core.py:1521) (1521-1534) | Case kiểm thử: ui error does not block finish or future callbacks. |
| [`RunLifecycleTests.test_finish_waits_for_old_thread_before_enabling_start`](E:/FacebookTool_Project/tests/test_core.py:1536) (1536-1547) | Case kiểm thử: finish waits for old thread before enabling start. |
| [`RunLifecycleTests.test_completed_run_can_start_again`](E:/FacebookTool_Project/tests/test_core.py:1549) (1549-1566) | Case kiểm thử: completed run can start again. |
| [`RunLifecycleTests.test_run_process_exception_and_cancel_always_schedule_finish`](E:/FacebookTool_Project/tests/test_core.py:1568) (1568-1583) | Case kiểm thử: run process exception and cancel always schedule finish. |
| [`RunLifecycleTests.test_thread_start_failure_restores_buttons_and_can_retry`](E:/FacebookTool_Project/tests/test_core.py:1585) (1585-1607) | Case kiểm thử: thread start failure restores buttons and can retry. |
| [`RunLifecycleTests.test_hung_close_is_bounded_and_other_resources_still_close`](E:/FacebookTool_Project/tests/test_core.py:1609) (1609-1627) | Case kiểm thử: hung close is bounded and other resources still close. |
| [`RunLifecycleTests.test_hung_close_is_bounded_and_other_resources_still_close.run [async]`](E:/FacebookTool_Project/tests/test_core.py:1610) (1610-1626) | Helper/mô phỏng phục vụ case test_hung_close_is_bounded_and_other_resources_still_close; không phải production flow. |
| [`RunLifecycleTests.test_hung_close_is_bounded_and_other_resources_still_close.run.hang [async]`](E:/FacebookTool_Project/tests/test_core.py:1612) (1612-1614) | Helper/mô phỏng phục vụ case test_hung_close_is_bounded_and_other_resources_still_close; không phải production flow. |
| [`RunLifecycleTests.test_manual_profile_close_cancels_only_its_worker`](E:/FacebookTool_Project/tests/test_core.py:1629) (1629-1643) | Case kiểm thử: manual profile close cancels only its worker. |
| [`RunLifecycleTests.test_manual_profile_close_cancels_only_its_worker.run [async]`](E:/FacebookTool_Project/tests/test_core.py:1630) (1630-1642) | Helper/mô phỏng phục vụ case test_manual_profile_close_cancels_only_its_worker; không phải production flow. |
| [`PageSetupRuntimeTests.setUp`](E:/FacebookTool_Project/tests/test_core.py:1647) (1647-1650) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`PageSetupRuntimeTests.test_creation_notice_on_same_url_allows_setup_not_success [async]`](E:/FacebookTool_Project/tests/test_core.py:1652) (1652-1661) | Case kiểm thử: creation notice on same url allows setup not success. |
| [`PageSetupRuntimeTests.test_other_page_notice_and_manage_text_are_not_accepted [async]`](E:/FacebookTool_Project/tests/test_core.py:1663) (1663-1666) | Case kiểm thử: other page notice and manage text are not accepted. |
| [`PageSetupRuntimeTests.test_toast_and_structural_contact_fields_are_supported [async]`](E:/FacebookTool_Project/tests/test_core.py:1668) (1668-1675) | Case kiểm thử: toast and structural contact fields are supported. |
| [`PageSetupRuntimeTests.make_button`](E:/FacebookTool_Project/tests/test_core.py:1677) (1677-1682) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`PageSetupRuntimeTests.test_inline_next_button_skips_hidden_and_disabled_controls [async]`](E:/FacebookTool_Project/tests/test_core.py:1684) (1684-1694) | Case kiểm thử: inline next button skips hidden and disabled controls. |
| [`PageSetupRuntimeTests.test_done_precedes_next_and_missing_controls_are_not_clicked [async]`](E:/FacebookTool_Project/tests/test_core.py:1696) (1696-1705) | Case kiểm thử: done precedes next and missing controls are not clicked. |
| [`PageMarginClickTests.setUp`](E:/FacebookTool_Project/tests/test_core.py:1709) (1709-1718) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`PageMarginClickTests.test_clicks_only_the_checked_blank_point [async]`](E:/FacebookTool_Project/tests/test_core.py:1720) (1720-1724) | Case kiểm thử: clicks only the checked blank point. |
| [`PageMarginClickTests.test_no_safe_margin_skips_click [async]`](E:/FacebookTool_Project/tests/test_core.py:1726) (1726-1730) | Case kiểm thử: no safe margin skips click. |
| [`PageMarginClickTests.test_stopped_run_does_not_click [async]`](E:/FacebookTool_Project/tests/test_core.py:1732) (1732-1736) | Case kiểm thử: stopped run does not click. |
| [`PageMarginClickTests.test_stop_after_point_selection_does_not_click [async]`](E:/FacebookTool_Project/tests/test_core.py:1738) (1738-1744) | Case kiểm thử: stop after point selection does not click. |
| [`PageMarginClickTests.test_stop_after_point_selection_does_not_click.select_then_stop [async]`](E:/FacebookTool_Project/tests/test_core.py:1739) (1739-1741) | Helper/mô phỏng phục vụ case test_stop_after_point_selection_does_not_click; không phải production flow. |
| [`PageMarginClickTests.test_optional_click_failure_does_not_change_account_status [async]`](E:/FacebookTool_Project/tests/test_core.py:1746) (1746-1750) | Case kiểm thử: optional click failure does not change account status. |
| [`PageMarginClickTests.test_checkpoint_cancels_without_click [async]`](E:/FacebookTool_Project/tests/test_core.py:1752) (1752-1757) | Case kiểm thử: checkpoint cancels without click. |
| [`PageMarginClickTests.test_concurrent_accounts_use_their_own_page [async]`](E:/FacebookTool_Project/tests/test_core.py:1759) (1759-1769) | Case kiểm thử: concurrent accounts use their own page. |
| [`PageWaitTests.setUp`](E:/FacebookTool_Project/tests/test_core.py:1773) (1773-1795) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`PageWaitTests.test_feed_runs_during_delay_and_not_before_deadline [async]`](E:/FacebookTool_Project/tests/test_core.py:1797) (1797-1805) | Case kiểm thử: feed runs during delay and not before deadline. |
| [`PageWaitTests.test_zero_delay_does_not_browse_or_sleep [async]`](E:/FacebookTool_Project/tests/test_core.py:1807) (1807-1810) | Case kiểm thử: zero delay does not browse or sleep. |
| [`PageWaitTests.test_countdown_uses_config_range_and_isolated_account_state [async]`](E:/FacebookTool_Project/tests/test_core.py:1812) (1812-1828) | Case kiểm thử: countdown uses config range and isolated account state. |
| [`PageWaitTests.test_stop_during_wait_never_resumes_creation [async]`](E:/FacebookTool_Project/tests/test_core.py:1830) (1830-1837) | Case kiểm thử: stop during wait never resumes creation. |
| [`PageWaitTests.test_stop_during_wait_never_resumes_creation.stop_on_scroll [async]`](E:/FacebookTool_Project/tests/test_core.py:1831) (1831-1833) | Helper/mô phỏng phục vụ case test_stop_during_wait_never_resumes_creation; không phải production flow. |
| [`PageWaitTests.test_closed_profile_and_network_errors_are_error_not_die [async]`](E:/FacebookTool_Project/tests/test_core.py:1839) (1839-1846) | Case kiểm thử: closed profile and network errors are error not die. |
| [`PageWaitTests.test_checkpoint_cancels_wait_and_clears_countdown [async]`](E:/FacebookTool_Project/tests/test_core.py:1848) (1848-1852) | Case kiểm thử: checkpoint cancels wait and clears countdown. |
| [`PageWaitTests.test_finalization_preserves_completed_results_and_account_status`](E:/FacebookTool_Project/tests/test_core.py:1854) (1854-1862) | Case kiểm thử: finalization preserves completed results and account status. |
| [`PageWaitTests.test_checkpoint_finalization_keeps_checkpoint_status`](E:/FacebookTool_Project/tests/test_core.py:1864) (1864-1869) | Case kiểm thử: checkpoint finalization keeps checkpoint status. |
| [`PageWaitTests.test_waiting_for_next_page_preserves_verified_results`](E:/FacebookTool_Project/tests/test_core.py:1871) (1871-1877) | Case kiểm thử: waiting for next page preserves verified results. |

### tests/test_targeted_runtime.py

364 dòng source; 30 khai báo hàm/callback, 0 class. Đây không phải số test cases.

| Hàm / vị trí | Trách nhiệm hoặc mục tiêu kiểm thử |
|---|---|
| [`make_app`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:14) (14-27) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`snapshot`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:30) (30-33) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`friend_resources`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:36) (36-46) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`test_disappearance_or_wrong_recipient_is_not_success`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:51) (51-58) | Case kiểm thử: disappearance or wrong recipient is not success. |
| [`test_matching_recipient_pending_is_sent`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:61) (61-66) | Case kiểm thử: matching recipient pending is sent. |
| [`test_existing_relationship_is_not_clicked`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:70) (70-76) | Case kiểm thử: existing relationship is not clicked. |
| [`test_friend_exception_is_task_error_not_account_die`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:79) (79-90) | Case kiểm thử: friend exception is task error not account die. |
| [`test_failed_unverified_click_is_not_repeated_for_same_account`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:93) (93-108) | Case kiểm thử: failed unverified click is not repeated for same account. |
| [`test_failed_unverified_click_is_not_repeated_for_same_account.run [async]`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:95) (95-106) | Helper/mô phỏng phục vụ case test_failed_unverified_click_is_not_repeated_for_same_account; không phải production flow. |
| [`test_proxy_rejects_missing_components`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:112) (112-113) | Case kiểm thử: proxy rejects missing components. |
| [`test_proxy_preserves_ipv6_and_decodes_password`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:122) (122-125) | Case kiểm thử: proxy preserves ipv6 and decodes password. |
| [`test_effective_proxy_obeys_selected_mode`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:129) (129-144) | Case kiểm thử: effective proxy obeys selected mode. |
| [`test_proxy_resolution_isolated_between_accounts`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:147) (147-154) | Case kiểm thử: proxy resolution isolated between accounts. |
| [`test_proxy_resolution_isolated_between_accounts.run [async]`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:150) (150-151) | Helper/mô phỏng phục vụ case test_proxy_resolution_isolated_between_accounts; không phải production flow. |
| [`test_empty_proxy_configuration_allows_direct_connection`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:158) (158-163) | Case kiểm thử: empty proxy configuration allows direct connection. |
| [`page_job`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:166) (166-168) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`page_evidence`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:171) (171-172) | Fixture/helper/probe cho kiểm thử; xem luồng tests ở mục 17. |
| [`test_page_rejects_unrelated_or_unproven_identity`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:176) (176-193) | Case kiểm thử: page rejects unrelated or unproven identity. |
| [`test_page_success_binds_owner_and_job`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:196) (196-200) | Case kiểm thử: page success binds owner and job. |
| [`test_category_matches_suggestion_and_verifies_selection`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:209) (209-231) | Case kiểm thử: category matches suggestion and verifies selection. |
| [`test_history_survives_reopen_refresh_and_reordering`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:234) (234-251) | Case kiểm thử: history survives reopen refresh and reordering. |
| [`test_history_never_stores_plaintext_credentials`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:254) (254-270) | Case kiểm thử: history never stores plaintext credentials. |
| [`test_concurrent_history_writes_and_duplicate_events`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:273) (273-285) | Case kiểm thử: concurrent history writes and duplicate events. |
| [`test_concurrent_history_writes_and_duplicate_events.save`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:276) (276-277) | Helper/mô phỏng phục vụ case test_concurrent_history_writes_and_duplicate_events; không phải production flow. |
| [`test_palette_complete_and_selection_readable`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:288) (288-295) | Case kiểm thử: palette complete and selection readable. |
| [`test_refresh_during_run_preserves_worker_account_and_proxy`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:298) (298-305) | Case kiểm thử: refresh during run preserves worker account and proxy. |
| [`test_selected_account_renders_persistent_history_only`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:308) (308-321) | Case kiểm thử: selected account renders persistent history only. |
| [`test_new_run_keeps_history_and_clears_only_task_results`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:324) (324-332) | Case kiểm thử: new run keeps history and clears only task results. |
| [`test_category_suggestions_absent_is_failed`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:335) (335-341) | Case kiểm thử: category suggestions absent is failed. |
| [`test_account_table_styles_work_in_both_real_tk_themes`](E:/FacebookTool_Project/tests/test_targeted_runtime.py:344) (344-364) | Case kiểm thử: account table styles work in both real tk themes. |

### tests/runtime_restart_probe.py

45 dòng source; 1 khai báo hàm/callback, 0 class. Đây không phải số test cases.

| Hàm / vị trí | Trách nhiệm hoặc mục tiêu kiểm thử |
|---|---|
| [`main`](E:/FacebookTool_Project/tests/runtime_restart_probe.py:12) (12-41) | Đọc/verify license và tạo vòng lặp app hoặc cửa sổ kích hoạt. |

Tổng inventory Python: **466 khai báo hàm/callback**, gồm **264 khai báo ngoài thư mục tests** và **202 khai báo trong tests/probe**; **29 class**. Nhiều hàm trong test là fake/helper, không phải 202 test cases.


## Phụ lục B. Hằng số và script được nhúng

Những khai báo dưới đây là các khối ngoài hàm trong `client_app.py`. Chúng được đọc bởi các helper/worker, không phải mỗi khối đều là một tác vụ riêng.

| Khai báo / vị trí | Vai trò |
|---|---|
| [CURRENT_VERSION](E:/FacebookTool_Project/client_app.py:47) | Phiên bản source; version checker và tiêu đề UI dùng giá trị này. |
| [VERSION_CHECK_URL](E:/FacebookTool_Project/client_app.py:48) | Nguồn metadata update. |
| [SECRET_SALT](E:/FacebookTool_Project/client_app.py:50) | Thành phần dẫn xuất khóa settings; không chép giá trị vào tài liệu. |
| [LICENSE_API_URL](E:/FacebookTool_Project/client_app.py:51) | Endpoint cấp phép, không phải endpoint automation Facebook. |
| [APP_DATA_DIR](E:/FacebookTool_Project/client_app.py:52), [LICENSE_FILE / SETTINGS_FILE](E:/FacebookTool_Project/client_app.py:57) | Đường dẫn dữ liệu cục bộ. |
| [SEARCH_KEYWORDS](E:/FacebookTool_Project/client_app.py:67) | Search fallback khi chưa cung cấp từ khóa. |
| [HO_VIET / DEM_VIET / TEN_VIET](E:/FacebookTool_Project/client_app.py:76), [HAU_TO_PAGE](E:/FacebookTool_Project/client_app.py:85) | Thành phần tên ngẫu nhiên dùng cho plan fallback. |
| [ADD_FRIEND_SELECTORS](E:/FacebookTool_Project/client_app.py:95), [FRIEND_REQUEST_SENT_SELECTORS](E:/FacebookTool_Project/client_app.py:117) | Selector gửi lời mời và nhận diện đã gửi/pending; có fallback ngôn ngữ. |
| [RESULT_FILE_LOCK](E:/FacebookTool_Project/client_app.py:128) | Lock shared output trong cùng process. |
| [ACCOUNT_STATUSES / LABELS](E:/FacebookTool_Project/client_app.py:130) | Các status và tên hiển thị. |
| [ACCOUNT_STATUS_COLORS / PALETTE](E:/FacebookTool_Project/client_app.py:139) | Màu account trong bảng và từng theme. |
| [TASK_RESULTS](E:/FacebookTool_Project/client_app.py:155) | Tập task result được store sử dụng. |
| [FRIEND_SCOPE_SNAPSHOT](E:/FacebookTool_Project/client_app.py:213) | JavaScript đọc vùng thao tác người nhận, connected/links/controls và friendship state để kiểm trước/sau click. |
| [PAGE_CREATION_EVIDENCE](E:/FacebookTool_Project/client_app.py:239) | JavaScript thu identity/tên/canonical từ DOM cho Page verification, không tự ghi success. |
| [LOGIN_SUCCESS / INVALID / TECHNICAL_ERROR](E:/FacebookTool_Project/client_app.py:270) | Ba kết quả helper login; cần caller xử lý đúng. |
| [PAGE_FLOW_STATES / PAGE_ACCESS_STATUSES](E:/FacebookTool_Project/client_app.py:326) | Tập bước Create Page và kết quả cấp quyền Page. |
| [MESSAGE_BTN_SELECTORS](E:/FacebookTool_Project/client_app.py:673), [CHAT_INPUT_SELECTORS](E:/FacebookTool_Project/client_app.py:680) | Fallback control nhắn tin/input chat. |
| [CANCEL_REQUEST_SELECTORS](E:/FacebookTool_Project/client_app.py:686), [FRIEND_STATE_SELECTORS](E:/FacebookTool_Project/client_app.py:694) | Hủy yêu cầu và nhận diện quan hệ friend/pending. |
| [CREATE_PAGE_BUTTON_PATTERN](E:/FacebookTool_Project/client_app.py:701), [ADD_PAGE_ADMIN_BUTTON_PATTERN](E:/FacebookTool_Project/client_app.py:706) | Regex label fallback cho nút tạo Page/thêm người. |
| [NEXT_BUTTON_PATTERN](E:/FacebookTool_Project/client_app.py:710), [FINISH / SKIP](E:/FacebookTool_Project/client_app.py:714) | Label fallback cho onboarding. |
| [PAGE_SETUP_FIELDS_SELECTOR](E:/FacebookTool_Project/client_app.py:716) | Tập input/field giúp nhận diện màn hình thiết lập. |
| [PAGE_BLANK_MARGIN_POINT](E:/FacebookTool_Project/client_app.py:726) | JavaScript tìm điểm nằm trong vùng trống, tránh control/dialog để click ngoài an toàn hơn. |
| [GIVE_ACCESS_BUTTON_PATTERN](E:/FacebookTool_Project/client_app.py:748) | Label fallback của nút cấp quyền. |
| [ACCOUNT_METADATA_PATTERN](E:/FacebookTool_Project/client_app.py:754) | Pattern cho helper metadata; parser chính hiện chưa nối helper này như đã lưu ý. |
| [PAGE_ACCESS_RESULT_FIELDS](E:/FacebookTool_Project/client_app.py:1034), [CREATE_PAGE_RESULT_FIELDS](E:/FacebookTool_Project/client_app.py:1095) | Header/schema CSV tương ứng. |
| [THEMES](E:/FacebookTool_Project/client_app.py:2027) | Màu nền, chữ, input, border và accent của bốn theme. |

Các JavaScript string trong phương thức browser dùng để đọc/đổi DOM hoặc khởi tạo context; updater string tạo batch/PowerShell helper Windows. Chúng được thực thi khi hàm tương ứng gọi evaluate/add_init_script/helper, không phải độc lập lúc Python import.

## Phụ lục C. Vị trí các hàm PowerShell và JavaScript

| File / hàm | Source |
|---|---|
| release.ps1 / param | [Dòng 2](E:/FacebookTool_Project/release.ps1:2) |
| Get-RequiredCommand | [Dòng 15](E:/FacebookTool_Project/release.ps1:15) |
| Invoke-NativeCapture | [Dòng 25](E:/FacebookTool_Project/release.ps1:25) |
| Invoke-NativeChecked | [Dòng 49](E:/FacebookTool_Project/release.ps1:49) |
| Write-Utf8NoBom | [Dòng 67](E:/FacebookTool_Project/release.ps1:67) |
| Set-JsonProperty | [Dòng 77](E:/FacebookTool_Project/release.ps1:77) |
| Remove-PathWithRetry | [Dòng 92](E:/FacebookTool_Project/release.ps1:92) |
| Invoke-PytestGate | [Dòng 126](E:/FacebookTool_Project/release.ps1:126) |
| license_worker / json | [Dòng 3](E:/FacebookTool_Project/license_worker/src/index.js:3) |
| normalizeKey | [Dòng 10](E:/FacebookTool_Project/license_worker/src/index.js:10) |
| isLicenseKey | [Dòng 14](E:/FacebookTool_Project/license_worker/src/index.js:14) |
| sha256 | [Dòng 18](E:/FacebookTool_Project/license_worker/src/index.js:18) |
| randomKey | [Dòng 24](E:/FacebookTool_Project/license_worker/src/index.js:24) |
| parseDuration | [Dòng 30](E:/FacebookTool_Project/license_worker/src/index.js:30) |
| validateLicense | [Dòng 35](E:/FacebookTool_Project/license_worker/src/index.js:35) |
| telegramSend | [Dòng 70](E:/FacebookTool_Project/license_worker/src/index.js:70) |
| handleTelegram | [Dòng 86](E:/FacebookTool_Project/license_worker/src/index.js:86) |
| export default.fetch / routes | [Dòng 150](E:/FacebookTool_Project/license_worker/src/index.js:150) |

## Phụ lục D. Snapshot và giới hạn tài liệu

| Python source | Số dòng | SHA256 snapshot |
|---|---:|---|
| `client_app.py` | 7563 | `f0b11eb1e17c671d18277cc7ddb6996fe797e45ef845119bfe65a3856790e089` |
| `account_history.py` | 132 | `885bf0c5fda8c780222fe9bddd19cd0a6a9ecbcf68bca151f42736887e69883b` |
| `admin_key_gen.py` | 7 | `341004c306b666cb06d50d0ba0bfe153ef81c03208b0128c57178f8503648996` |
| `tests/test_core.py` | 1881 | `0b83ae9211e7e46fcee7122e1741c143dc4206696514b827371855c6041f326b` |
| `tests/test_targeted_runtime.py` | 364 | `3514646ad7278a44ba7c4347df406f2c9f2a8ae39755e873f0c60f04183dd870` |
| `tests/runtime_restart_probe.py` | 45 | `a716433c9e3074cd691503f97ee7f55ab97071da7aec459f774b2558daecf60c` |

SHA256 bổ sung:

- `release.ps1`: `3281fe657c831f11d17a14c488873280a9cee21f432954b287b16ad6173df79a`.

Snapshot giúp nhận biết source đã đổi; các hash này không phải hash của EXE phát hành.

Tài liệu sẽ cần cập nhật khi source đổi. Liên kết dòng chỉ chính xác với snapshot này. Những secret/tài khoản riêng, dữ liệu lịch sử thật và binary không được chép vào đây. Chỉ file tài liệu được thêm, không có logic ứng dụng được sửa trong quá trình bàn giao này.
