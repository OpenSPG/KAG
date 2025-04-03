import os
import copy
import httpx
from asyncio import sleep

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
async def map_geocode(address: str, ctx: Context) -> dict:
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
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/geocoding/v3/"

        # 设置请求参数
        # 更多参数信息请参考:https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-geocoding
        params = {
            "ak": f"{api_key}",
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
async def map_reverse_geocode(latitude: float, longitude: float, ctx: Context) -> dict:
    """
    Name:
        逆地理编码服务

    Description:
        根据经纬度坐标点获取对应位置的行政区划与POI信息

    Args:
        latitude: 纬度 (gcj02ll)
        longitude: 经度 (gcj02ll)

    """
    try:
        # 获取API密钥
        if not api_key:
            raise Exception("There")

        # 调用百度API
        url = f"{api_url}/reverse_geocoding/v3/"

        # 设置请求参数
        # 更多参数信息请参考:https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-geocoding-abroad
        params = {
            "ak": f"{api_key}",
            "output": "json",
            "coordtype": "gcj02ll",
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
async def map_search_places(
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
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/place/v2/search"

        # 设置请求参数
        # 更多参数信息请参考:https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-placeapi
        params = {
            "ak": f"{api_key}",
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
async def map_place_details(uid: str, ctx: Context) -> dict:
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
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/place/v2/detail"

        # 设置请求参数
        # 更多参数信息请参考:https://lbsyun.baidu.com/faq/api?title=webapi/guide/webservice-placeapi/detail
        params = {
            "ak": f"{api_key}",
            "output": "json",
            "uid": f"{uid}",
            # Agent入参不可控，这里给定scope为2
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
async def map_distance_matrix(
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
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/routematrix/v2/{mode}"

        # 设置请求参数
        # 更多参数信息请参考:https://lbsyun.baidu.com/faq/api?title=webapi/routchtout
        params = {
            "ak": f"{api_key}",
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
async def map_directions(
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
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/directionlite/v1/{model}"

        # 设置请求参数
        # 更多参数信息请参考:https://lbs.baidu.com/faq/api?title=webapi/direction-api-v2
        params = {
            "ak": f"{api_key}",
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
async def map_weather(location: str, district_id: int, ctx: Context) -> dict:
    """
    Name:
        天气查询服务

    Description:
        用户可通过行政区划或是经纬度坐标查询实时天气信息及未来5天天气预报(注意: 使用经纬度坐标需要高级权限)。

    Args:
        location: 经纬度，经度在前纬度在后，逗号分隔 (需要高级权限, 例如: 116.30815,40.056878)
        district_id: 行政区划 (例如: 1101010)
    """
    try:
        # 获取API密钥
        if not api_key:
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/weather/v1/?"

        # 设置请求参数
        # 更多参数信息请参考:https://lbs.baidu.com/faq/api?title=webapi/weather
        params = {"ak": f"{api_key}", "data_type": "all", "from": "py_mcp"}

        # 核心入参，二选一
        if not location:
            params["district_id"] = f"{district_id}"
        else:
            params["location"] = f"{location}"

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
async def map_ip_location(
    # ip: str,
    ctx: Context,
) -> dict:
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
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/location/ip"

        # 设置请求参数
        # 更多参数信息请参考:https://lbs.baidu.com/faq/api?title=webapi/ip-api
        params = {"ak": f"{api_key}", "from": "py_mcp"}

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
async def map_road_traffic(
    model: str,
    road_name: str,
    city: str,
    bounds: str,
    vertexes: str,
    center: str,
    radius: int,
    ctx: Context,
) -> dict:
    """
    Name:
        实时路况查询服务

    Description:
        查询实时交通拥堵情况, 可通过指定道路名和区域形状(矩形, 多边形, 圆形)进行实时路况查询。

        道路实时路况查询: 查询具体道路的实时拥堵评价和拥堵路段、拥堵距离、拥堵趋势等信息
        矩形区域实时路况查询: 查询指定矩形地理范围的实时拥堵情况和各拥堵路段信息
        多边形区域实时路况查询: 查询指定多边形地理范围的实时拥堵情况和各拥堵路段信息
        圆形区域(周边)实时路况查询: 查询某中心点周边半径范围内的实时拥堵情况和各拥堵路段信息


    Args:
        model:      路况查询类型(road, bound, polygon, around)
        road_name:  道路名称和道路方向, model=road时必传 (如:朝阳路南向北)
        city:       城市名称或城市adcode, model=road时必传 (如:北京市)
        bounds:     区域左下角和右上角的经纬度坐标, model=bound时必传 (如:39.912078,116.464303;39.918276,116.475442)
        vertexes:   多边形区域的顶点经纬度, model=polygon时必传 (如:39.910528,116.472926;39.918276,116.475442;39.916671,116.459056;39.912078,116.464303)
        center:     圆形区域的中心点经纬度坐标, model=around时必传 (如:39.912078,116.464303)
        radius:     圆形区域的半径(米), 取值[1,1000], model=around时必传 (如:200)

    """
    try:
        # 获取API密钥
        if not api_key:
            raise Exception("Can not found API key.")

        # 调用百度API
        url = f"{api_url}/traffic/v1/{model}?"

        # 设置请求参数
        # 更多参数信息请参考:https://lbs.baidu.com/faq/api?title=webapi/traffic
        params = {"ak": f"{api_key}", "output": "json", "from": "py_mcp"}

        # 核心入参，根据model选择
        # match model:
        #     case 'bound':
        #         params['bounds'] = f'{bounds}'
        #     case 'polygon':
        #         params['vertexes'] = f'{vertexes}'
        #     case 'around':
        #         params['center'] = f'{center}'
        #         params['radius'] = f'{radius}'
        #     case 'road':
        #         params['road_name'] = f'{road_name}'
        #         params['city'] = f'{city}'
        #     case _:
        #         pass

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
async def map_poi_extract(text_content: str, ctx: Context) -> dict:
    """
    Name:
        POI智能提取

    Description:
        根据用户提供的文本描述信息, 智能提取出文本中所提及的POI相关信息. (注意: 使用该服务, api_key需要拥有对应的高级权限, 否则会报错)

    Args:
        text_content: 用于提取POI的文本描述信息 (完整的旅游路线，行程规划，景点推荐描述等文本内容, 例如: 新疆独库公路和塔里木湖太美了, 从独山子大峡谷到天山神秘大峡谷也是很不错的体验)
    """

    # 关于高级权限使用的相关问题，请联系我们: https://lbsyun.baidu.com/apiconsole/fankui?typeOne=%E4%BA%A7%E5%93%81%E9%9C%80%E6%B1%82&typeTwo=%E9%AB%98%E7%BA%A7%E6%9C%8D%E5%8A%A1

    try:
        # 获取API密钥
        if not api_key:
            raise Exception("Can not found API key.")

        # 调用POI智能提取的提交接口
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        submit_url = f"{api_url}/api_mark/v1/submit"
        result_url = f"{api_url}/api_mark/v1/result"

        # 设置上传用户描述的请求体
        submit_body = {
            "ak": f"{api_key}",
            "id": 0,
            "msg_type": "text",
            "text_content": f"{text_content}",
            "from": "py_mcp",
        }

        # 异步请求
        async with httpx.AsyncClient() as client:
            # 提交任务
            submit_resp = await client.post(
                submit_url, data=submit_body, headers=headers, timeout=10.0
            )
            submit_resp.raise_for_status()
            submit_result = submit_resp.json()

            if submit_result.get("status") != 0:
                error_msg = submit_result.get("message", "unkown error")
                raise Exception(f"API response error: {error_msg}")

            map_id = submit_result.get("result", {}).get("map_id")
            if not map_id:
                raise Exception("Can not found map_id")

            # 轮询获取结果（最多5次，间隔2秒）
            result_body = {"ak": api_key, "id": 0, "map_id": map_id, "from": "py_mcp"}
            max_retries = 5
            for attempt in range(max_retries):
                result_resp = await client.post(
                    result_url, data=result_body, headers=headers, timeout=10.0
                )
                result_resp.raise_for_status()
                result = result_resp.json()

                if result.get("status") == 0 and result.get("result"):
                    return result
                elif attempt < max_retries - 1:
                    await sleep(2)

            else:
                raise Exception("Timeout to get the result")

        if result.get("status") != 0:
            error_msg = result.get("message", "unkown error")
            raise Exception(f"API response error: {error_msg}")

    except httpx.HTTPError as e:
        raise Exception(f"HTTP request failed: {str(e)}") from e
    except KeyError as e:
        raise Exception(f"Failed to parse reponse: {str(e)}") from e


if __name__ == "__main__":
    mcp.run()
