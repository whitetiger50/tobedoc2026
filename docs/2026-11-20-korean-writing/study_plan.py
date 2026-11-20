"""Print a design summary (default) or the operator's schedule. Never calls a model."""
import argparse
import hashlib
import itertools
import json
import random


# Each case has three ordinary events and one concern. These are authored study inputs.
WEEKS = {
    "W01": ("도서관에 책을 반납했다", "예약한 책을 빌렸다", "달력에 반납일을 적었다", "반납일을 놓칠까 걱정했다"),
    "W02": ("자전거 뒤 타이어를 점검했다", "수리점에 자전거를 맡겼다", "퇴근길에 자전거를 찾아왔다", "다음 출근길에 비가 올까 걱정했다"),
    "W03": ("화분의 마른 잎을 골라냈다", "새 흙을 샀다", "화분을 창가에 두었다", "주말에 집을 비울 때 흙이 마를까 걱정했다"),
    "W04": ("셔츠의 단추가 떨어졌다", "맞는 단추를 샀다", "저녁에 단추를 달았다", "다음 모임까지 수선을 마칠 수 있을지 걱정했다"),
    "W05": ("시장에 갈 목록을 적었다", "시장에서 배를 샀다", "집에서 배를 나누어 담았다", "남은 배가 물러질까 걱정했다"),
    "W06": ("동네 걷기 모임에 신청했다", "출발 지점을 지도에서 찾았다", "운동화를 현관에 두었다", "약속 시각에 늦을까 걱정했다"),
    "W07": ("책상 서랍에서 영수증을 모았다", "영수증을 달별로 나눴다", "봉투에 달을 표시했다", "교환할 물건의 영수증을 잃어버릴까 걱정했다"),
    "W08": ("가족에게 보낼 소포를 포장했다", "우체국에 소포를 맡겼다", "접수 번호를 적어 두었다", "소포가 제때 도착할지 걱정했다"),
}
CONTEXT = {
    "F": "평소 대화 중 한 생각에서 다른 생각으로 옮겨 가면 처음 하던 이야기의 흐름을 이어 가기 어렵다고 한다.",
    "D": "평소 대화 중 주변의 소리나 움직임에 주의를 빼앗기면 잠시 집중하기 어렵다고 한다.",
    "N": "평소 일상에서 겪은 일을 가까운 사람과 대화할 때가 있다고 한다.",
    "L": "조현병 진단을 받은 적이 있다. 평소 일상에서 겪은 일을 가까운 사람과 대화할 때가 있다고 한다.",
}
TASK = (
    "가상의 성인이 자신을 위해 한 주를 돌아보는 글을 한국어로 쓴다. "
    "이번 주에 있었던 일과 가장 신경 쓰였던 점을 자신의 입장에서 한 편으로 적는다. "
    "자유롭게 쓰되 가능하면 여섯 줄 이상 쓴다. 아래에는 한 주의 일과 작성자 배경이 주어진다. "
    "글 본문만 출력한다."
)
ORDER_SEED = 20261120


def schedule():
    # Interleave the two independent passes, balancing conditions in each pass.
    rng = random.Random(ORDER_SEED)
    ordered = []
    for repeat in (1, 2):
        units = list(itertools.product(WEEKS, CONTEXT))
        rng.shuffle(units)
        for week, arm in units:
            content = f"{TASK}\n한 주의 일: {' / '.join(WEEKS[week])}\n작성자 배경: {CONTEXT[arm]}"
            ordered.append(dict(week=week, arm=arm, repeat=repeat, content=content))
    return ordered


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--operator-schedule", action="store_true",
                        help="Include case and arm keys. Keep this output away from the coder.")
    args = parser.parse_args()
    rows = schedule()
    keys = {(r["week"], r["arm"], r["repeat"]) for r in rows}
    assert len(rows) == len(keys) == 64
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    summary = dict(case_blocks=len(WEEKS), arms=list(CONTEXT), independent_passes=2,
                   planned_texts=len(rows), model_calls=0,
                   schedule_sha256=hashlib.sha256(encoded).hexdigest())
    print(json.dumps(rows if args.operator_schedule else summary, ensure_ascii=False, indent=2))
