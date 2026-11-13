"""Deterministic demo dataset for ``DEMO_MODE``.

Why this exists: the product is only convincing when it has mail in it, and a
reviewer (competition judge, colleague, future user) will never type a real
app password into someone else's instance. So demo mode ships a fixed,
obviously-fake mailbox set: four accounts, ~70 mails, already analysed and
partly handled, so every screen — dashboard, priority queue, search, reports,
schedule — has something meaningful to show on first load.

Design rules
------------
* Fake by construction: every message id ends in ``@demo.mailigence.local`` and
  every account points at ``demo.invalid``, so nothing here can ever be synced
  against a real server.
* Idempotent: seeding is skipped when a demo account already exists; the reset
  endpoint deletes the demo accounts (cascading to their mail) and re-seeds.
* No AI calls: ``analyzed_at`` / ``category`` / ``priority_score`` are filled in
  directly, so a demo instance works with no model configured.
* Deterministic: no randomness — screenshots and the demo video stay stable.
"""
from __future__ import annotations

import html as html_lib
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import MailDirection, UnifiedEmail
from app.models.email_account import AuthType, EmailAccount, SyncStatus
from app.models.email_category import EmailCategory

DEMO_IMAP_SERVER = "demo.invalid"
DEMO_DOMAIN = "demo.mailigence.local"

# name -> display label. Labels are Chinese because the demo audience is the
# Chinese market (QQ / 163 users); ``name`` is the stable key stored on mail.
_CATEGORIES: list[tuple[str, str, str]] = [
    ("work", "工作", "#4a9eff"),
    ("meeting", "会议", "#9b6dff"),
    ("finance", "财务", "#f0a020"),
    ("notice", "通知", "#5ec48a"),
    ("marketing", "广告", "#8a8f98"),
    ("personal", "个人", "#ff7a9c"),
    ("school", "学校", "#24b3b3"),
]

_ACCOUNTS: list[dict] = [
    {
        "platform": "gmail",
        "email": "lin.wei@gmail.com",
        "display_name": "林薇 · 工作邮箱",
        "color": "#ea4335",
    },
    {
        "platform": "outlook",
        "email": "chen.hao@contoso.com",
        "display_name": "陈皓 · 公司邮箱",
        "color": "#0f6cbd",
    },
    {
        "platform": "qq",
        "email": "882366115@qq.com",
        "display_name": "林薇 · QQ 邮箱",
        "color": "#12b7f5",
    },
    {
        "platform": "163",
        "email": "linwei_notice@163.com",
        "display_name": "林薇 · 163 邮箱",
        "color": "#d33a3a",
    },
]

# (account index, days ago, hour, sender, sender address, subject, snippet,
#  category, priority, suggested action, is_ad, is_read, handled days ago)
_MAILS: list[tuple] = [
    (0, 0, 9, "王倩", "wang.qian@acme-tech.cn", "【周会】需求评审改到周三 14:00", "会议室 B-302，请提前把评审材料发群里。", "meeting", 88, "reply", False, False, None),
    (0, 0, 8, "张明", "zhang.ming@acme-tech.cn", "Q4 路线图初稿，今天下班前帮忙扫一眼", "重点看第 3 节的排期是否和客户端依赖冲突。", "work", 85, "reply", False, False, None),
    (0, 0, 10, "HR 共享中心", "hr@acme-tech.cn", "11 月社保基数确认（今天 18:00 截止）", "请在员工自助平台完成确认，逾期默认沿用上月基数。", "work", 78, "reply", False, False, None),
    (0, 1, 14, "李静", "li.jing@client-alpha.com", "关于合同第 3 条的修改意见", "付款周期希望从 60 天调整为 45 天，其余条款我们认可。", "finance", 82, "reply", False, False, None),
    (0, 1, 20, "会议助手", "meeting@acme-tech.cn", "明天 10:00 与客户 Alpha 的对接会", "已为你预订会议室 A-201，参会 6 人。", "meeting", 86, "reply", False, True, None),
    (0, 2, 11, "GitHub", "notifications@github.com", "[mailigence] PR #482 请求你审核", "fix: keep PostgreSQL running when the launcher window closes", "work", 62, "review", False, True, None),
    (0, 3, 16, "财务共享中心", "finance@acme-tech.cn", "10 月差旅报销已到账", "报销单 BX-20261026 已打款 ¥1,860.00。", "finance", 40, "notice", False, True, 2),
    (0, 3, 9, "Stripe", "receipts@stripe.com", "发票 #INV-2026-0912 已支付 ¥2,400", "感谢付款，发票可在后台下载。", "finance", 45, "notice", False, True, 3),
    (0, 4, 15, "日历", "calendar-notification@google.com", "提醒：周五 16:00 项目复盘", "议程模板已附在会议邀请里。", "meeting", 70, "notice", False, True, 2),
    (0, 4, 18, "陈皓", "chen.hao@contoso.com", "麻烦把上周的复盘文档发我", "我这边要同步给客户。", "work", 74, "reply", False, False, None),
    (0, 5, 12, "快递 100", "service@kuaidi100.com", "您的包裹已到达菜鸟驿站", "取件码 8-2-1043，请于 3 日内领取。", "notice", 20, "ignore", False, True, 5),
    (0, 6, 7, "招商银行", "creditcard@cmbchina.com", "信用卡账单已出账 ¥3,286.40", "最后还款日 11 月 28 日，最低还款 ¥328.64。", "finance", 55, "notice", False, True, 6),
    (0, 0, 11, "家长群", "noreply@school-news.cn", "三年级二班家长会通知（本周四 19:00）", "请回复是否参加，需要统计座位。", "school", 72, "reply", False, False, None),
    (0, 2, 21, "飞书", "no-reply@feishu.cn", "你被 @ 了：项目群 · 3 条新消息", "张明：评审材料我放在共享文档里了。", "notice", 50, "review", False, False, None),
    (1, 0, 9, "Alpha 采购", "purchase@client-alpha.com", "询价：企业版 200 席位报价请周五前给到", "另外请附上一年期与三年期的价格对比。", "work", 90, "reply", False, False, None),
    (1, 0, 13, "法务", "legal@contoso.com", "NDA 用印流程已发起，需你确认", "请在法务系统第 2 步点击确认，流程才能继续。", "work", 76, "reply", False, False, None),
    (1, 1, 17, "周报机器人", "bot@contoso.com", "本周团队周报汇总（待你补充）", "还有 2 位成员未提交，补齐后自动合并。", "work", 65, "reply", False, True, None),
    (1, 2, 10, "客户 Alpha 财务", "ap@client-alpha.com", "付款申请已提交，发票请寄至新地址", "收件地址已变更，请注意不要寄旧地址。", "finance", 80, "reply", False, False, None),
    (1, 3, 8, "Microsoft 365", "no-reply@microsoft.com", "你的订阅将于 12 月续费", "续费金额 ¥398.00，可在管理后台关闭自动续费。", "notice", 30, "ignore", False, True, 3),
    (1, 5, 14, "供应商 Beta", "sales@vendor-beta.com", "双十一企业采购折扣方案", "满 50 席位享 85 折，有效期至 11 月 20 日。", "marketing", 8, "ignore", True, True, 4),
    (2, 0, 8, "班主任", "teacher@school.edu.cn", "数学作业与期中考试范围", "考试范围第 1-4 单元，作业请周一前提交。", "school", 68, "review", False, False, None),
    (2, 1, 19, "老同学 张磊", "zhang.lei@qq.com", "周末聚一下？", "老地方，周六中午，能来吗？", "personal", 60, "reply", False, False, None),
    (2, 1, 9, "顺丰速运", "sf-express@sf.com", "快件签收提醒", "您的快件已由本人签收。", "notice", 15, "ignore", False, True, 1),
    (2, 2, 16, "腾讯会议", "meeting@tencent.com", "会议录制已生成：产品评审", "录制链接 30 天内有效。", "notice", 35, "review", False, True, 2),
    (2, 3, 10, "工商银行", "95588@icbc.com.cn", "账户变动提醒 -¥199.00", "交易时间 11 月 10 日 10:12，商户：网易严选。", "finance", 50, "notice", False, True, 3),
    (2, 6, 20, "网易严选", "edm@mail.163.com", "会员日 5 折，仅剩 6 小时", "全场会员专享，错过再等一月。", "marketing", 3, "ignore", True, True, 5),
    (3, 0, 7, "12306", "12306@rails.com.cn", "购票成功：11 月 18 日 G102 北京南—上海虹桥", "08:00 开，07:45 前完成检票，座位 05 车 12A。", "notice", 66, "review", False, False, None),
    (3, 2, 11, "中国移动", "10086@139.com", "本月流量使用提醒", "已使用 18.6G / 30G，超出部分按 5 元/G 计费。", "notice", 18, "ignore", False, True, 2),
    (3, 3, 9, "京东金融", "notice@jd.com", "还款提醒：11 月 20 日到期", "本期应还 ¥1,240.00，可设置自动还款。", "finance", 58, "review", False, False, None),
]

# Filler mail keeps the reports/charts realistic without hand-writing 40 rows.
# They are all promotional or low-value notifications, so the priority queue
# stays focused on the curated set above.
_FILLER_SENDERS: list[tuple[str, str, str]] = [
    ("极客时间", "news@geekbang.org", "本周上新：AI Agent 实战训练营"),
    ("京东", "no-reply@jd.com", "11.11 大促最后 6 小时"),
    ("知乎日报", "daily@zhihu.com", "今天最值得读的 8 个回答"),
    ("产品经理社区", "weekly@pmnote.cn", "每周精选：B 端产品的 5 个误区"),
    ("网易云音乐", "noreply@music.163.com", "你的 2026 年度听歌报告已生成"),
    ("阿里云", "message@aliyun.com", "ECS 实例月度账单已出"),
    ("掘金", "weekly@juejin.cn", "本周前端热榜 TOP 10"),
    ("大众点评", "edm@dianping.com", "附近新店 5 折尝鲜"),
]

_FILLER_CATEGORIES = ["marketing", "marketing", "notice", "marketing", "marketing", "notice", "marketing", "marketing"]


def _body_text(snippet: str) -> str:
    return (
        f"{snippet}\n\n"
        "（演示数据：这封邮件由 Mailigence 演示模式生成，用于展示 AI 归类、"
        "优先级排序与每日简报的效果，不对应任何真实邮箱。）"
    )


def _body_html(snippet: str) -> str:
    return "<p>" + html_lib.escape(snippet) + "</p><p><em>演示数据，非真实邮件。</em></p>"


def _message_id(index: int) -> str:
    return f"<demo-{index:03d}@{DEMO_DOMAIN}>"


async def _ensure_categories(db: AsyncSession) -> None:
    existing = {
        name
        for name in (await db.execute(select(EmailCategory.name))).scalars().all()
    }
    for name, label, color in _CATEGORIES:
        if name in existing:
            continue
        db.add(EmailCategory(name=name, label=label, color=color, is_system=True))
    await db.flush()


async def _demo_accounts(db: AsyncSession) -> list[EmailAccount]:
    rows = await db.execute(
        select(EmailAccount).where(EmailAccount.imap_server == DEMO_IMAP_SERVER)
    )
    return list(rows.scalars().all())


async def seed_demo_data(db: AsyncSession) -> int:
    """Insert the demo mailboxes if they are missing. Returns accounts created."""
    if await _demo_accounts(db):
        return 0

    await _ensure_categories(db)
    now = datetime.now(timezone.utc)

    accounts: list[EmailAccount] = []
    for spec in _ACCOUNTS:
        account = EmailAccount(
            platform=spec["platform"],
            email=spec["email"],
            auth_type=AuthType.APP_PASSWORD,
            # Never decrypted: demo mode blocks every sync path that would call
            # resolve_credential(). Anything non-empty satisfies the column.
            credential_secret="demo",
            imap_server=DEMO_IMAP_SERVER,
            imap_port=993,
            display_name=spec["display_name"],
            color=spec["color"],
            sync_status=SyncStatus.IDLE,
            last_synced_at=now,
        )
        db.add(account)
        accounts.append(account)
    await db.flush()

    mails: list[UnifiedEmail] = []
    index = 0
    for (
        acct_idx, days_ago, hour, sender, addr, subject, snippet,
        category, priority, action, is_ad, is_read, handled_days_ago,
    ) in _MAILS:
        received = (now - timedelta(days=days_ago)).replace(
            hour=hour, minute=(index * 7) % 60, second=0, microsecond=0
        )
        handled = (
            None
            if handled_days_ago is None
            else (now - timedelta(days=handled_days_ago)).replace(
                hour=min(hour + 1, 23), minute=(index * 11) % 60, second=0, microsecond=0
            )
        )
        mails.append(
            UnifiedEmail(
                account_id=accounts[acct_idx].id,
                platform=accounts[acct_idx].platform,
                message_id=_message_id(index),
                thread_id=_message_id(index),
                direction=MailDirection.INBOX,
                sender=sender,
                sender_email=addr,
                recipients=[accounts[acct_idx].email],
                subject=subject,
                body_snippet=snippet,
                body_text=_body_text(snippet),
                body_html=_body_html(snippet),
                received_at=received,
                is_read=is_read,
                has_reply=False,
                raw_headers={},
                category=category,
                is_advertisement=is_ad,
                priority_score=priority,
                summary=snippet,
                suggested_action=action,
                analyzed_at=received,
                handled_at=handled,
            )
        )
        index += 1

    for filler_idx in range(38):
        sender, addr, subject = _FILLER_SENDERS[filler_idx % len(_FILLER_SENDERS)]
        acct_idx = filler_idx % len(accounts)
        days_ago = filler_idx % 13
        hour = 7 + (filler_idx * 3) % 14
        received = (now - timedelta(days=days_ago)).replace(
            hour=hour, minute=(filler_idx * 13) % 60, second=0, microsecond=0
        )
        snippet = "这是一封演示用的订阅/推广邮件，用于展示批量归类与广告过滤效果。"
        mails.append(
            UnifiedEmail(
                account_id=accounts[acct_idx].id,
                platform=accounts[acct_idx].platform,
                message_id=_message_id(index),
                thread_id=_message_id(index),
                direction=MailDirection.INBOX,
                sender=sender,
                sender_email=addr,
                recipients=[accounts[acct_idx].email],
                subject=subject,
                body_snippet=snippet,
                body_text=_body_text(snippet),
                body_html=_body_html(snippet),
                received_at=received,
                is_read=True,
                has_reply=False,
                raw_headers={},
                category=_FILLER_CATEGORIES[filler_idx % len(_FILLER_CATEGORIES)],
                is_advertisement=True,
                priority_score=5,
                summary=snippet,
                suggested_action="ignore",
                analyzed_at=received,
                # Half of them already dismissed: the "minutes saved" card and
                # the ad panel both look alive on first load.
                handled_at=received if filler_idx % 2 == 0 else None,
            )
        )
        index += 1

    db.add_all(mails)
    await db.commit()
    return len(accounts)


async def reset_demo_data(db: AsyncSession) -> int:
    """Delete the demo mailboxes (mail cascades) and re-seed. Returns count."""
    accounts = await _demo_accounts(db)
    for account in accounts:
        # Delete explicitly instead of relying on ON DELETE CASCADE: the
        # constraint only exists on databases created by this build.
        await db.execute(
            delete(UnifiedEmail).where(UnifiedEmail.account_id == account.id)
        )
        await db.delete(account)
    await db.commit()
    return await seed_demo_data(db)
