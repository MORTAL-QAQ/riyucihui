# -*- coding: utf-8 -*-
"""向 frontend/css/desktop.css 追加「词级呈现模式徽章」样式（UTF-8，幂等）。

用法：cd backend && python dev_tools/append_mode_css.py
"""
import io
import os

CSS = """

/* ══════════════ 词级呈现模式徽章（被试内实验） ══════════════ */
.mode-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  white-space: nowrap;
  vertical-align: middle;
}
.mode-badge.multimodal {
  background: #eef2ff;
  color: #4f46e5;
  border: 1px solid rgba(99, 102, 241, 0.25);
}
.mode-badge.text-only {
  background: #f3f4f6;
  color: #4b5563;
  border: 1px solid #e5e7eb;
}
/* 未选中具体词单时，呈现模式相关按钮置灰（仍可点击以给出提示） */
#btn-set-modes:disabled,
#btn-export-bindings:disabled {
  cursor: not-allowed;
}
"""


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = os.path.join(root, "frontend", "css", "desktop.css")
    with io.open(path, encoding="utf-8") as f:
        text = f.read()
    if "词级呈现模式徽章" in text:
        print("呈现模式样式已存在，跳过")
        return 0
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text.rstrip("\n") + "\n" + CSS)
    print(f"已追加呈现模式样式，{len(CSS)} 字符")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
