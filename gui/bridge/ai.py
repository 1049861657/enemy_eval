"""AI 评价域：设置、人设、请求预览、生成与采纳的纯逻辑。

一次评价的世代号与请求快照由 `ReviewSession` 持有：换卡或换数据即作废在飞结果，
采纳前再比对一次快照，避免把旧点评写到已改动的卡上。
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

from models import AiEvaluationResult, EnemyData
from utils.ai.baseline import load_baseline
from utils.ai.client import build_current_payload
from utils.ai.prompt import (
    CONTRACT,
    DEFAULT_PERSONA,
    effective_persona,
    persona_for_storage,
    render_preview,
)
from utils.app.ai_prefs import (
    AiRequestConfig,
    ai_base_url_preview,
    ai_request_config,
    save_ai_persona,
    save_ai_settings,
)
from utils.app.settings import load_app_settings
from utils.errors import FileOperationError, categorize_error_message

if TYPE_CHECKING:
    from gui.card_model import CardModel

BASELINE_HINT = "无法读取杰斯顿基准数据：\n\n{error}\n\n请确认安装完整（resource/baseline/）。"


class ReviewSession:
    """一次 AI 评价的世代号、结果与请求快照。"""

    def __init__(self) -> None:
        self._revision = 0
        self._current: dict[str, Any] = {}
        self.comment = ""

    def begin(self, current: dict[str, Any]) -> int:
        """开始一次请求：记下快照并推进世代号，返回本次世代号。"""
        self._revision += 1
        self._current = current
        return self._revision

    def invalidate(self) -> None:
        """换卡或换数据：在飞结果作废，已展示的结果一并清空。"""
        self._revision += 1
        self._current = {}
        self.comment = ""

    def accepts(self, revision: int) -> bool:
        """该世代号是否仍是当前世代。"""
        return revision == self._revision

    def keep_comment(self, comment: str) -> None:
        """记下可用结果（调用方已确认世代号有效）。"""
        self.comment = comment

    def data_unchanged(self, card_model: CardModel) -> bool:
        """请求之后卡片数据是否没动过。"""
        return build_current_payload(card_model.enemy_data) == self._current


def base_url() -> str:
    """设置框预填的地址。"""
    return load_app_settings().ai_base_url


def model() -> str:
    """设置框预填的模型名。"""
    return load_app_settings().ai_model


def api_key() -> str:
    """设置框预填的密钥（明文存偏好）。"""
    return load_app_settings().ai_api_key


def configured() -> bool:
    """三要素是否齐备；判定与调用层同源。"""
    return ai_request_config() is not None


def request_config() -> AiRequestConfig | None:
    """可用的调用配置；缺任一要素返回 None。"""
    return ai_request_config()


def persona_text() -> str:
    """面板打开时预填的人设：偏好里的自定义值，未自定义则为内置默认。"""
    return effective_persona()


def default_persona() -> str:
    """内置默认人设，供面板「恢复默认」使用。"""
    return DEFAULT_PERSONA


def contract_text() -> str:
    """输出契约全文（只读展示）。"""
    return CONTRACT


def base_url_preview(url: str) -> str:
    """该地址最终请求到的完整 URL；只用于显示，不阻止保存。"""
    return ai_base_url_preview(url)


def save_settings(url: str, name: str, key: str) -> None:
    """写入 AI 配置；形状非法抛 ValueError，写盘失败抛 FileOperationError。"""
    save_ai_settings(url, name, key)


def save_persona(persona: str) -> None:
    """人设落盘（与内置默认相同则存空串）；写盘失败抛 FileOperationError。"""
    save_ai_persona(persona_for_storage(persona))


def request_preview(card_model: CardModel, persona: str) -> str:
    """预览组装后实际会发出的两条 message；基准缺失时返回错误文案（不抛）。"""
    try:
        baseline = load_baseline()
    except FileOperationError as error:
        return f"基准数据不可用：{error}"
    return render_preview(
        persona=persona,
        baseline=baseline,
        current=build_current_payload(card_model.enemy_data),
    )


def load_review_baseline() -> dict[str, Any]:
    """评价用基准数据；缺失抛 FileOperationError。"""
    return load_baseline()


def baseline_error_hint(error: Exception) -> str:
    """基准缺失的展示文案（含安装提示）。"""
    return BASELINE_HINT.format(error=error)


def begin_review(
    card_model: CardModel, persona: str, session: ReviewSession
) -> tuple[EnemyData, int, str]:
    """开一次评价：深拷卡片快照、推进世代号、给出本次人设文本（空白即内置默认）。"""
    snapshot = card_model.enemy_data.model_copy(deep=True)
    revision = session.begin(build_current_payload(snapshot))
    return snapshot, revision, persona.strip() or DEFAULT_PERSONA


def accept_result(result: AiEvaluationResult, revision: int, session: ReviewSession) -> bool:
    """结果回主线程：世代号不符返回 False（调用方提示"已作废"），否则记下正文。"""
    if not session.accepts(revision):
        return False
    session.keep_comment(result.comment)
    return True


def error_message(error: Exception) -> tuple[str, str]:
    """异常的展示文案：标题 + 正文（按异常子类分类）。"""
    return categorize_error_message(error)


def comment_decision(card_model: CardModel, text: str, session: ReviewSession) -> str:
    """采纳判决：`empty`（空内容）/ `confirm`（请求后数据已变，需二次确认）/ `write`。"""
    if not text.strip():
        return "empty"
    if not session.data_unchanged(card_model):
        return "confirm"
    return "write"


def write_comment(card_model: CardModel, comment: str) -> None:
    """写入当前卡简评：一步入撤销栈，不写文件。"""
    card_model.update_properties({"brief_comment": comment.strip()})
