import ast
import pathlib
import unittest

import client_app


class CoreHelpersTest(unittest.TestCase):
    def test_version_comparison_is_numeric(self):
        self.assertGreater(client_app.version_tuple("2.10.0"), client_app.version_tuple("2.9.9"))

    def test_update_url_must_be_trusted_executable(self):
        self.assertTrue(
            client_app.is_trusted_update_url(
                "https://github.com/phat-boop/facebook-auto-tool/releases/download/v2.1.3/client_app.exe"
            )
        )
        self.assertFalse(client_app.is_trusted_update_url("http://github.com/file.exe"))
        self.assertFalse(client_app.is_trusted_update_url("https://example.com/file.exe"))
        self.assertFalse(client_app.is_trusted_update_url("https://github.com/releases"))

    def test_cookie_parser_preserves_values(self):
        cookies = client_app.parse_cookies("c_user=123; xs=abc=def;")
        self.assertEqual(cookies[0]["name"], "c_user")
        self.assertEqual(cookies[1]["value"], "abc=def")

    def test_proxy_parser_supports_authenticated_and_scheme_formats(self):
        self.assertEqual(
            client_app.parse_proxy("127.0.0.1:8080:user:pass"),
            {
                "server": "http://127.0.0.1:8080",
                "username": "user",
                "password": "pass",
            },
        )
        self.assertEqual(
            client_app.parse_proxy("socks5://user:pass@127.0.0.1:1080")["server"],
            "socks5://127.0.0.1:1080",
        )
        self.assertIsNone(client_app.parse_proxy("127.0.0.1:99999"))

    def test_concurrency_limit_protects_large_queues(self):
        self.assertEqual(client_app.MainToolApp._bounded_int("100", 6, 1, 20), 20)

    def test_create_page_button_languages(self):
        for label in ("Tạo Trang", "Create Page", "Créer une Page", "Crear página", "Criar Página"):
            self.assertIsNotNone(client_app.CREATE_PAGE_BUTTON_PATTERN.fullmatch(label))

    def test_async_methods_do_not_read_tk_widgets(self):
        source_path = pathlib.Path(client_app.__file__)
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        forbidden_prefixes = (
            "self.ent_",
            "self.txt_",
            "self.chk_",
            "self.proxy_mode",
            "self.mode_vars",
            "self.tree",
            "self.root",
        )
        violations = []
        for function in ast.walk(tree):
            if not isinstance(function, ast.AsyncFunctionDef):
                continue
            for node in ast.walk(function):
                if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                    continue
                owner = ast.unparse(node.func.value)
                if node.func.attr == "get" and owner.startswith(forbidden_prefixes):
                    violations.append(f"{function.name}:{node.lineno}:{owner}.get")
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
