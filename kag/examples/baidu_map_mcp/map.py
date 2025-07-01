# map.py
import os
import copy
import httpx

from mcp.server.fastmcp import FastMCP, Context

# 创建MCP服务器实例
mcp = FastMCP("mcp-server-baidu-maps")
# 设置API密钥，用于调用百度地图API，获取方式请参考：https://lbsyun.baidu.com/apiconsole/key
api_key = os.getenv("BAIDU_MAPS_API_KEY")
print(os.environ)
print(f"api_key = {api_key}")
if not api_key:
    raise ValueError("missing api key")
api_url = "https://api.map.baidu.com"


def filter_result(data) -> dict:
    """
    过滤路径规划结果，用于剔除冗余字段信息，保证输出给模型的数据更简洁，避免长距离路径规划场景下chat中断
    """

    # 创建输入数据的深拷贝以避免修改原始数据
    processed_data = copy.deepcopy(data)

    # 检查是否存在'result'键
    if "result" in processed_data:
        result = processed_data["result"]

        # 检查'result'中是否存在'routes'键
        if "routes" in result:
            for route in result["routes"]:
                # 检查每个'route'中是否存在'steps'键
                if "steps" in route:
                    new_steps = []
                    for step in route["steps"]:
                        # 提取'instruction'字段，若不存在则设为空字符串
                        new_step = {
                            "distance": step.get("distance", ""),
                            "duration": step.get("duration", ""),
                            "instruction": step.get("instruction", ""),
                        }
                        new_steps.append(new_step)
                    # 替换原steps为仅含instruction的新列表
                    route["steps"] = new_steps

    return processed_data


@mcp.tool()
async def reverse_geocode_v3(latitude: float, longitude: float, ctx: Context) -> dict:
    """
    Name:
        逆地理编码服务

    Description:
        将坐标点转换为对应语义化地址

    Args:
        latitude: 纬度 (WGS84坐标系)
        longitude: 经度 (WGS84坐标系)

    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("There")

        # 调用百度API
        url = f"{api_url}/reverse_geocoding/v3/"
        params = {
            "ak": api_key,
            "output": "json",
            "coordtype": "wgs84ll",
            "location": f"{latitude},{longitude}",
            "extensions_poi": "1",
            "from": "py_mcp",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def geocoder_v2(address: str, ctx: Context) -> dict:
    """
    Name:
        地理编码服务

    Description:
        将地址解析为对应的位置坐标。地址结构越完整，地址内容越准确，解析的坐标精度越高。

    Args:
        address: 待解析的地址。最多支持84个字节。可以输入两种样式的值，分别是：
        1、标准的结构化地址信息，如北京市海淀区上地十街十号【推荐，地址结构越完整，解析精度越高】
        2、支持“*路与*路交叉口”描述方式，如北一环路和阜阳路的交叉路口
        第二种方式并不总是有返回结果，只有当地址库中存在该地址描述时才有返回。

    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/geocoding/v3/"
        params = {
            "ak": api_key,
            "output": "json",
            "address": f"{address}",
            "from": "py_mcp",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def place_v2_search(
    query: str, region: str, location: str, radius: int, ctx: Context
) -> dict:
    """
    Name:
        地点检索服务

    Description:
        城市内检索: 检索某一城市内（目前最细到城市级别）的地点信息。
        周边检索: 设置圆心和半径，检索圆形区域内的地点信息（常用于周边检索场景）。

    Args:
        query: 检索关键字
        region: 检索的行政区划
        location: 圆形区域检索中心点
        radius: 圆形区域检索半径，单位：米

    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/place/v2/search"
        params = {
            "ak": api_key,
            "output": "json",
            "query": f"{query}",
            "region": f"{region}",
            "from": "py_mcp",
        }
        if location:
            params["location"] = f"{location}"
            params["radius"] = f"{radius}"

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def place_v2_detail(uid: str, ctx: Context) -> dict:
    """
    Name:
        地点详情检索服务

    Description:
        地点详情检索: 地点详情检索针对指定POI，检索其相关的详情信息。
        开发者可以通地点检索服务获取POI uid。使用“地点详情检索”功能，传入uid，即可检索POI详情信息，如评分、营业时间等（不同类型POI对应不同类别详情数据）。

    Args:
        uid: poi的唯一标识
    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/place/v2/detail"
        params = {
            "ak": api_key,
            "output": "json",
            "uid": f"{uid}",
            "scope": 2,
            "from": "py_mcp",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def routematrix_v2_driving(
    origins: str, destinations: str, mode: str, ctx: Context
) -> dict:
    """
    Name:
        批量算路服务

    Description:
        根据起点和终点坐标计算路线规划距离和行驶时间
        批量算路目前支持驾车、骑行、步行
        步行时任意起终点之间的距离不得超过200KM，超过此限制会返回参数错误
        驾车批量算路一次最多计算100条路线，起终点个数之积不能超过100

    Args:
        origins: 多个起点坐标纬度,经度，按|分隔。示例：40.056878,116.30815|40.063597,116.364973【骑行】【步行】支持传入起点uid提升绑路准确性，格式为：纬度,经度;POI的uid|纬度,经度;POI的uid。示例：40.056878,116.30815;xxxxx|40.063597,116.364973;xxxxx
        destinations: 多个终点坐标纬度,经度，按|分隔。示例：40.056878,116.30815|40.063597,116.364973【【骑行】【步行】支持传入终点uid提升绑路准确性，格式为：纬度,经度;POI的uid|纬度,经度;POI的uid。示例：40.056878,116.30815;xxxxx|40.063597,116.364973;xxxxx
        mode: 批量算路类型(driving, riding, walking)

    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/routematrix/v2/" + mode
        params = {
            "ak": api_key,
            "output": "json",
            "origins": f"{origins}",
            "destinations": f"{destinations}",
            "from": "py_mcp",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def directionlite_v1(
    model: str, origin: str, destination: str, ctx: Context
) -> dict:
    """
    Name:
        路线规划服务

    Description:
        驾车路线规划: 根据起终点坐标规划驾车出行路线
        骑行路线规划: 根据起终点坐标规划骑行出行路线
        步行路线规划: 根据起终点坐标规划步行出行路线
        公交路线规划: 根据起终点坐标规划公共交通出行路线

    Args:
        model: 路线规划类型(driving, riding, walking, transit)
        origin: 起点坐标，当用户只有起点名称时，需要先通过地理编码服务或地点地点检索服务确定起点的坐标
        destination: 终点坐标，当用户只有起点名称时，需要先通过地理编码服务或地点检索服务确定起点的坐标

    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/directionlite/v1/{model}"
        params = {
            "ak": api_key,
            "output": "json",
            "origin": f"{origin}",
            "destination": f"{destination}",
            "from": "py_mcp",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        """
        过滤非公交的导航结果，防止返回的结果中包含大量冗余坐标信息，影响大模型的响应速度，或是导致chat崩溃。
        当前只保留导航结果每一步的距离、耗时和语义化信息。
        公交路线规划情况比较多，尽量全部保留。
            
        """
        if model == "transit":
            return result
        else:
            return filter_result(result)

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def weather_v1(
    # location: str,
    district_id: int,
    ctx: Context,
) -> dict:
    """
    Name:
        天气查询服务

    Description:
        用户可通过坐标查询实时天气信息及未来5天天气预报。

    Args:

        district_id: 行政区划
    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/weather/v1/?"
        params = {
            "ak": api_key,
            # "location": f"{location}",
            "district_id": f"{district_id}",
            "data_type": "now",
            "from": "py_mcp",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


@mcp.tool()
async def location_ip(ctx: Context) -> dict:
    """
    Name:
        IP定位服务

    Description:
        根据用户请求的IP获取当前的位置，当需要知道用户当前位置、所在城市时可以调用该工具获取

    Args:

    """
    try:
        # 获取API密钥
        if not api_key:
            raise error_msg("The r")

        # 调用百度API
        url = f"{api_url}/location/ip"
        params = {"ak": api_key, "from": "py_mcp"}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result = response.json()

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

        return result

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


if __name__ == "__main__":
    mcp.run()
