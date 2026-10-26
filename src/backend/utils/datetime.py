# 把datetime转为ISO-8601,把ISO-8601转为datetime格式

from datetime import datetime, timezone, timedelta


def get_future_time(hour: str, days: int = 1) -> datetime:
    """获取明天（或 N 天后）x点的日期 (带东八区时区)
    hour:小时
    days：往后退几天，默认1天
    return 带时区的datetime对象

    """

    # 1. 将传入的字符串小时转为整数（支持传入 "9" 或 "09"）
    target_hour = int(hour)

    # 2. 定义东八区时区 (+08:00)
    tz_utc8 = timezone(timedelta(hours=8))

    # 3. 获取当前带时区的时间
    now = datetime.now(tz_utc8)

    # 4. 加上一天获取明天，然后替换成指定的时分秒
    target_time = (now + timedelta(days=days)).replace(
        hour=target_hour, minute=0, second=0, microsecond=0
    )

    return target_time


def dt_to_iso(dt: datetime) -> str:
    """
    将 datetime 转为带时区的 ISO-8601 字符串 (无微秒)
    例如: '2022-11-28T00:00:00+08:00'
    """
    # 如果没有时区信息，默认按东八区（北京时间）处理
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))

    # timespec='seconds' 会去掉微秒，只保留到秒
    return dt.isoformat(timespec="seconds")


def iso_to_dt(iso_str: str) -> datetime:
    if iso_str.endswith("Z"):
        iso_str = iso_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(iso_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    return dt


# 从明天的x点起，到days的那个时间，从上午9-12，下午2-6的时间，把每小时平均分割起来，然后和我传过来是时间段进行相比，如果有
# 时间段不在 每小时之间的，就属于 空闲时间 ，找到一个，返回出来


def find_free_slot(
    start_time: datetime, end_time: datetime, existing_events: list
) -> tuple | None:
    """
    查找空闲时间段
    :param start_time: 查询范围的开始时间 (带时区)
    :param end_time: 查询范围的结束时间 (带时区)
    :param existing_events: 已有的日程列表，格式为 [({'dateTime': 'xxx'}, {'dateTime': 'xxx'}), ...]
    :return: 返回一个空闲元组 (free_start, free_end)，如果没有空闲返回 None
    """
    # 1. 生成标准工作时段 (上午 9-12，下午 14-18，按 1 小时切分)
    work_slots = []
    current_day = start_time.replace(hour=0, minute=0, second=0, microsecond=0)

    # 一直生成到 end_time 所在的那天
    while current_day <= end_time:
        # 判断是否周末（可选）：如果是周末，可以跳过
        if current_day.weekday() >= 5:
            current_day += timedelta(days=1)
            continue

        # 上午时段: 9:00 - 12:00 (循环生成 9-10, 10-11, 11-12)
        for h in range(9, 12):
            slot_start = current_day.replace(hour=h)
            slot_end = current_day.replace(hour=h + 1)
            work_slots.append((slot_start, slot_end))

        # 下午时段: 14:00 - 18:00 (循环生成 14-15, 15-16, 16-17, 17-18)
        for h in range(14, 18):
            slot_start = current_day.replace(hour=h)
            slot_end = current_day.replace(hour=h + 1)
            work_slots.append((slot_start, slot_end))

        current_day += timedelta(days=1)

    # 2. 将你的日程转为统一的 datetime 对象格式
    busy_slots = []
    for event in existing_events:
        # 兼容字典 {'dateTime': '...'} 或者直接字符串传入
        s_str = event[0]["dateTime"] if isinstance(event[0], dict) else event[0]
        e_str = event[1]["dateTime"] if isinstance(event[1], dict) else event[1]

        s_dt = datetime.fromisoformat(s_str)
        e_dt = datetime.fromisoformat(e_str)
        busy_slots.append((s_dt, e_dt))

    # 3. 核心逻辑：从工作时段中剔除已被占用的时间，寻找空闲
    for slot_start, slot_end in work_slots:
        # 过滤出和当前标准时段有交集的所有日程
        overlaps = []
        for b_start, b_end in busy_slots:
            # 判断时间重叠的公式：开始1 < 结束2 且 结束1 > 开始2
            if slot_start < b_end and slot_end > b_start:
                overlaps.append((b_start, b_end))

        # 如果没有交集，说明整个 1 小时都是空闲的，直接返回！
        if not overlaps:
            return slot_start, slot_end

        # 如果有交集，把当前的 1 小时减去交集部分，看剩下有没有空
        # 对交集按开始时间排序
        overlaps.sort(key=lambda x: x[0])

        # 从当前时段的起点开始找
        cursor = slot_start
        for o_start, o_end in overlaps:
            # 如果日程开始时间晚于当前指针，说明中间有空隙（空闲时间）
            if o_start > cursor:
                # 只要空隙大于一定长度（比如 30分钟），就认为是空闲
                if (o_start - cursor).total_seconds() >= 1800:
                    return cursor, o_start
            # 指针移动到日程结束时间（不能倒退）
            cursor = max(cursor, o_end)

        # 检查最后一个日程结束后，到标准时段结束前，是否还有空隙
        if cursor < slot_end:
            if (slot_end - cursor).total_seconds() >= 1800:
                return cursor, slot_end

    # 所有时间都被排满了，返回 None
    return None
