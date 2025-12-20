"""
ManicTime SQL查询常量

将所有SQL查询语句集中管理，便于维护和测试。
"""

# 活动查询SQL（连接活动表和分组表获取完整信息）
ACTIVITY_QUERY = """
    SELECT 
        a.ReportId,
        a.ActivityId,
        a.GroupId,
        a.StartUtcTime,
        a.EndUtcTime,
        a.SourceId,
        a.Other,
        g.CommonId,
        g.Name as GroupName,
        g.Key as GroupKey,
        cg.Key as AppKey,
        cg.Name as AppName,
        cg.UpperKey
    FROM Ar_Activity a
    LEFT JOIN Ar_Group g ON a.ReportId = g.ReportId AND a.GroupId = g.GroupId
    LEFT JOIN Ar_CommonGroup cg ON g.CommonId = cg.CommonId
    WHERE a.StartUtcTime >= ? AND a.EndUtcTime <= ?
    ORDER BY a.StartUtcTime
"""

# 原始活动查询SQL（不含JOIN）
RAW_ACTIVITY_QUERY = """
    SELECT ReportId, ActivityId, GroupId, StartUtcTime, EndUtcTime, 
           SourceId, Other
    FROM Ar_Activity
    WHERE StartUtcTime >= ? AND EndUtcTime <= ?
    ORDER BY StartUtcTime
"""

# 应用列表查询SQL
APPLICATION_QUERY = """
    SELECT 
        CommonId,
        ReportGroupType,
        Key,
        Name,
        Color,
        UpperKey
    FROM Ar_CommonGroup
    WHERE ReportGroupType = 1
    ORDER BY Name
"""

# 日汇总查询SQL
DAY_SUMMARY_QUERY = """
    SELECT 
        abd.CommonId,
        cg.Name,
        SUM(abd.TotalSeconds) as TotalSeconds
    FROM Ar_ApplicationByDay abd
    LEFT JOIN Ar_CommonGroup cg ON abd.CommonId = cg.CommonId
    WHERE date(abd.Hour) = date(?)
    GROUP BY abd.CommonId, cg.Name
    ORDER BY TotalSeconds DESC
"""

# 获取最后同步时间
LAST_SYNC_QUERY = "SELECT MAX(EndUtcTime) as LastTime FROM Ar_Activity"

# 获取活动数量
ACTIVITY_COUNT_QUERY = "SELECT COUNT(*) as Count FROM Ar_Activity"

# 获取日期范围
DATE_RANGE_QUERY = """
    SELECT 
        MIN(StartUtcTime) as MinTime,
        MAX(EndUtcTime) as MaxTime
    FROM Ar_Activity
"""
