import requests
import re
import pandas as pd
from bs4 import BeautifulSoup
import time

# 在 https://github.com/Votess4All/COVID-19-SH-2022 基础上修改
# 适用于2022年4月6日及之后的数据爬取及位置匹配


def get_city_disease_info_after_0406(
        shanghaifabu_url,
        city_name="上海市"):
    """
    给定一篇上海发布的文章，找到相关区内公布的具体感染人群所在地址
    例如：shanghaifabu_url = "https://mp.weixin.qq.com/s/djwW3S9FUYBE2L5Hj94a3A"
    """
    r = requests.get(shanghaifabu_url)
    demo = r.text

    soup = BeautifulSoup(demo, 'html.parser')

    # 文本信息定位
    location_div = soup.find("div", attrs={"class": "rich_media_content"})

    # 区名定位
    locate_section_div = location_div.findAll(
        "section", attrs={"data-role": "title"})

    # 居住地信息定位，注意locate_section_div_1[2:]是后面使用的数据
    locate_section_div_1 = location_div.findAll(
        "section", attrs={"data-autoskip": "1"})

    city_name = "上海市"

    if len(locate_section_div) == len(locate_section_div_1[2:]):
        for i in range(len(locate_section_div)):
            area_name = locate_section_div[i].find("strong").text

            ps = locate_section_div_1[2:][i].findAll("p")
            area_xiaoqu = []
            for j, area_ps in enumerate(ps):
                if j <= 1 or j >= len(ps)-2:
                    continue

                area_xiaoqu.append(f"{city_name}"+area_name +
                                   area_ps.text.strip("，"))
            city_area_street[f"{city_name}"].append({area_name: area_xiaoqu})
    else:
        print('区名标题栏与地址栏数量不相等')

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

    filtername = ['安亭镇', '南翔镇', '江桥镇', '马陆镇',
                  '嘉定镇街道', '嘉定工业区', '徐行镇',
                  '华亭镇', '外冈镇', '新成路街道',
                  '真新街道', '菊园新区']

    reslist = []
    for addlist in df['loc_name'].str.split("、"):
        if len(addlist) > 1:
            jiedaoname = jiedaoMatch(filtername, addlist)

            for i in range(len(addlist)):
                if i == 0:
                    reslist.append(addlist[i])
                else:
                    reslist.append(jiedaoname+addlist[i])
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
            r = requests.get(url, params=dicts, timeout=10)
        except:
            # 如果碰到无法使用的key，换用另一个正常的key
            key = 'Another key'
            dicts['ak'] = key
            r = requests.get(url, params=dicts, timeout=10)

        try:
            res = r.json()
        except:
            print("当前地点:"+str(address))
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
                except:
                    print("KeyError! 当前地点:"+str(address))

            else:
                location.append(address)
                locationinfo.append('Nah')
                addr.append('Nah')

        else:
            print(str(address)+'status='+str(res['status']))
            location.append(address)
            locationinfo.append('Nah')
            addr.append('Nah')

        time.sleep(2)

    resultdf = pd.DataFrame({'location': location, 'locationinfo': locationinfo,
                             'addr': addr})

    return resultdf
