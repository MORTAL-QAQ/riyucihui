#!/bin/bash
# 生产端到端验证：实验流程（生成 20 词 → 配图 2 张抽样 → 测试提交 → 管理统计）
BASE="https://127.0.0.1"
U="exptest_$(date +%s)"

echo "=== 1. 注册测试账号 ==="
TOKEN=$(curl -sk -X POST "$BASE/api/register" -H 'Content-Type: application/json' \
  -d "{\"username\":\"$U\",\"password\":\"Exp123456\",\"name\":\"实验测试\"}" \
  | python3 -c 'import sys,json;print(json.load(sys.stdin).get("access_token",""))')
echo "token_len=${#TOKEN}"

echo "=== 2. 创建实验会话（生成 20 词，约 10-30s） ==="
RESP=$(curl -sk --max-time 120 -X POST "$BASE/api/experiment/sessions" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d '{"topic":"食物料理","level":"N3"}')
echo "$RESP" > /tmp/exp_session.json
python3 - << 'PYEOF'
import json
d = json.load(open('/tmp/exp_session.json'))
print("session_id:", d.get("session_id"), "topic:", d.get("topic"), "total:", d.get("total"))
words = d.get("words", [])
mm = [w for w in words if w["is_multimodal"]]
pl = [w for w in words if not w["is_multimodal"]]
print(f"多模态 {len(mm)} 个 / 非多模态 {len(pl)} 个")
assert len(words) == 20 and len(mm) == 10 and len(pl) == 10, "分组数量异常"
print("多模态样例:", mm[0]["japanese"], "| 有例句:", bool(mm[0].get("example_ja")))
print("非多模态样例:", pl[0]["japanese"], "| 字段:", sorted(pl[0].keys()))
assert "example_ja" not in pl[0] and "image_base64" not in pl[0], "非多模态不应含图文"
print("学习阶段数据隔离正确 ✅（非多模态无例句/图片字段）")
PYEOF

SID=$(python3 -c "import json;print(json.load(open('/tmp/exp_session.json'))['session_id'])")
MMID=$(python3 -c "import json;d=json.load(open('/tmp/exp_session.json'));print([w['id'] for w in d['words'] if w['is_multimodal']][0])")

echo "=== 3. 生成 1 张配图抽样（约 10-30s） ==="
curl -sk --max-time 90 -X POST "$BASE/api/experiment/words/$MMID/image" \
  -H "Authorization: Bearer $TOKEN" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("配图字节数:", len(d.get("image_base64","")))'

echo "=== 4. 取测试题 ==="
curl -sk "$BASE/api/experiment/sessions/$SID/quiz" -H "Authorization: Bearer $TOKEN" > /tmp/exp_quiz.json
python3 - << 'PYEOF'
import json
d = json.load(open('/tmp/exp_quiz.json'))
q = d.get("quiz", [])
print("题目数:", len(q))
print("样例题:", q[0]["japanese"], "选项:", q[0]["options"])
assert len(q) == 20 and len(q[0]["options"]) == 4, "题量或选项数异常"
# 生成作答（全选第一个选项）
answers = [{"word_id": x["word_id"], "choice": x["options"][0]} for x in q]
json.dump(answers, open('/tmp/exp_answers.json','w'))
print("测试题结构正确 ✅")
PYEOF

echo "=== 5. 提交测试 ==="
curl -sk -X POST "$BASE/api/experiment/sessions/$SID/test" \
  -H 'Content-Type: application/json' -H "Authorization: Bearer $TOKEN" \
  -d "{\"answers\":$(cat /tmp/exp_answers.json)}" > /tmp/exp_result.json
python3 - << 'PYEOF'
import json
d = json.load(open('/tmp/exp_result.json'))
print("多模态:", d["multimodal"], "\n非多模态:", d["plain"], "\n差值:", d["diff"])
assert d["multimodal"]["total"] == 10 and d["plain"]["total"] == 10
print("结果统计正确 ✅")
PYEOF

echo "=== 6. 清理测试账号 ==="
cd /opt/riyucihui
docker compose exec -T postgres psql -U jpvocab -d jpvocab -c "DELETE FROM users WHERE username LIKE 'exptest_%';" 2>&1 | tail -1
