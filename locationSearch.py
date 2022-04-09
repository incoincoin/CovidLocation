import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
import time

# 在 https://github.com/Votess4All/COVID-19-SH-2022 基础上修改
"""
3月1日以来，上海发布微信公众号每日公布感染者居住地信息或涉疫地址信息，格式有以下几种：
1. 3月1日: 该病例涉及的轨迹为xxx，xxx。
2. 3月2日: 居住在xxx，
3. 3月3日: 居住于xxx。
4. 3月4日: 居住于xxx，
5. 3月6日: 居住地为xxx，
6. 3月7日-3月17日: 居住于xxx，
7. 3月18日-4月5日: 单独发布居住地信息，各区之间用一个文本框显示。
8. 4月6日及之后: 单独发布居住地信息，各区居住地信息用文本框显示。

3月1日-3月6日的文本，使用简单的正则表达式即可单独提取。
3月7日-3月17日的文本，可使用同一规则提取。
3月18日-4月5日的文本，使用 get_city_disease_info 函数提取。
4月6日及之后，使用 get_city_disease_info_after_0406 函数提取。
"""


def get_city_disease_info_after_0406(shanghaifabu_url, city_name="上海市"):
    """
    适用于2022年4月6日及之后的数据爬取及位置匹配
    给定一篇上海发布的文章，找到相关区内公布的具体感染人群所在地址
    例如：shanghaifabu_url = "https://mp.weixin.qq.com/s/djwW3S9FUYBE2L5Hj94a3A"
    """
    r = requests.get(shanghaifabu_url)
    demo = r.text

    soup = BeautifulSoup(demo, 'html.parser')

    # 文本信息定位
    location_div = soup.find("div", attrs={"class": "rich_media_content"})

    # 区名定位
    locate_section_div = location_div.findAll("section",
                                              attrs={"data-role": "title"})

    # 居住地信息定位，注意locate_section_div_1[2:]是后面使用的数据
    locate_section_div_1 = location_div.findAll("section",
                                                attrs={"data-autoskip": "1"})

    city_area_street = {f"{city_name}": []}
    if len(locate_section_div) == len(locate_section_div_1[2:]):
        for i in range(len(locate_section_div)):
            area_name = locate_section_div[i].find("strong").text

            ps = locate_section_div_1[2:][i].findAll("p")
            area_xiaoqu = []
            for j, area_ps in enumerate(ps):
                if j <= 1 or j >= len(ps) - 2:
                    continue

                area_xiaoqu.append(f"{city_name}" + area_name +
                                   area_ps.text.strip("，"))
            city_area_street[f"{city_name}"].append({area_name: area_xiaoqu})
    else:
        print('区名标题栏与地址栏数量不相等')

    return city_area_street


def get_city_disease_info(shanghaifabu_url, city_name="上海市"):
    """
    适用于2022年3月18日-2022年4月5日的数据爬取及位置匹配
    给定一篇上海发布的文章，找到相关区内公布的具体感染人群所在地址
    例如：shanghaifubu_url = "https://mp.weixin.qq.com/s/w8UqtdmBtdLQitM7emOVjw"
    """

    r = requests.get(shanghaifabu_url)
    demo = r.text

    soup = BeautifulSoup(demo, 'html.parser')
    location_div = soup.find("div", attrs={"class": "rich_media_content"})
    locate_section_div = location_div.findAll("section",
                                              attrs={"data-role": "title"})

    city_area_street = {f"{city_name}": []}
    for i, sub_div in enumerate(locate_section_div):

        # strong: 加粗显示
        area_name = sub_div.find("strong").text
        ps = sub_div.findAll("p")

        area_xiaoqu = []
        for j, area_ps in enumerate(ps):
            if j <= 1 or j >= len(ps) - 2:
                continue

            area_xiaoqu.append(f"{city_name}" + area_name +
                               area_ps.text.strip("，"))
        city_area_street[f"{city_name}"].append({area_name: area_xiaoqu})

    return city_area_street


def jiedaoMatch(filtername, addlist):
    """
    找到嘉定区街道、镇的名字，并返回
    输入: filtername, 嘉定区街道镇列表
    输出：对应
    """

    outflag = -1
    for jiedao in filtername:

        # 定位出现街道名的位置
        flag = addlist[0].find(jiedao)
        # 未匹配
        if flag == -1:
            continue

        # 匹配到
        else:
            outflag = 0
            flag += len(jiedao)
            return addlist[0][:flag]
    if outflag == -1:
        print(addlist[0])
        print("该地址未匹配街道名")


def jiadingProcess(data):

    df = data[data['area_name'] == '嘉定区']

    filtername = [
        '安亭镇', '南翔镇', '江桥镇', '马陆镇', '嘉定镇街道', '嘉定工业区', '徐行镇', '华亭镇', '外冈镇',
        '新成路街道', '真新街道', '菊园新区'
    ]

    reslist = []
    for addlist in df['loc_name'].str.split("、"):
        if len(addlist) > 1:
            jiedaoname = jiedaoMatch(filtername, addlist)

            for i in range(len(addlist)):
                if i == 0:
                    reslist.append(addlist[i])
                else:
                    reslist.append(jiedaoname + addlist[i])
        else:
            reslist.append(addlist[0])

    temp = pd.DataFrame({'area_name': '嘉定区', 'loc_name': reslist})
    dataother = data[(data['area_name'] != '嘉定区')]
    datanew = pd.concat([dataother, temp]).reset_index(drop=True)

    return datanew


def transfertodf(city_disease_info, city_name="上海市"):

    shanghai_info = city_disease_info[city_name]

    datas = []

    for q, qu in enumerate(shanghai_info):

        if not (list(qu.values()) == [[]]):

            df_list = []
            for key, value in qu.items():

                jiedaos = value

                for jiedao in jiedaos:
                    df_list.append({
                        "area_name": key,
                        "loc_name": jiedao,
                    })

            df = pd.DataFrame(df_list, columns=df_list[0].keys())
            datas.append(df)

    datas = pd.concat(datas).reset_index(drop=True)
    # 去除重复，因为普陀区地址有时候会重复
    datas = datas.drop_duplicates().reset_index(drop=True)

    # 嘉定区地址处理

    datas = jiadingProcess(datas)

    # 去除 loc_name 中的标点符号 如逗号，句号等
    datas['loc_name'] = datas['loc_name'].str.replace(r'[^\w\s]', '')
    return datas


def getCoordinatesFromBaidu(data, locstring):

    location = []
    locationinfo = []
    addr = []

    for address in data[locstring]:

        url = 'http://api.map.baidu.com/place/v2/search?'
        key = 'your key'
        dicts = {
            'query': address,
            'region': '上海市',
            'city_limit': 'true',
            'scope': 1,
            'coord_type': 3,  # bd09，注意，是整数型int
            'output': 'json',
            'ak': key
        }
        try:
            r = requests.get(url, params=dicts, timeout=(20, 20))
            res = r.json()
        except requests.exceptions.ConnectTimeout:
            print("当前地点:" + str(address) + "ConnectionError")
            location.append(address)
            locationinfo.append('Nah')
            addr.append('Nah')
            continue

        # 判断 status=0
        if res['status'] == 0:

            # 判断res['result']是否为空
            if res['results']:
                try:
                    location.append(address)
                    locationinfo.append(res['results'][0]['location'])
                    addr.append(res['results'][0]['address'])
                except KeyError:
                    print("KeyError! 当前地点:" + str(address))

            else:
                location.append(address)
                locationinfo.append('Nah')
                addr.append('Nah')

        else:
            print(str(address) + 'status=' + str(res['status']))
            location.append(address)
            locationinfo.append('Nah')
            addr.append('Nah')

        time.sleep(2)

    resultdf = pd.DataFrame({
        'location': location,
        'locationinfo': locationinfo,
        'addr': addr
    })

    return resultdf
