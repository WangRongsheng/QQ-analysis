# -*- coding: utf-8 -*-
# 2017/6/14 21:50
"""
-------------------------------------------------------------------------------
Function:   monitor data in this place
Version:    1.0
Author:     SLY
Contact:    slysly759@gmail.com 

code is far away from bugs with the god Animal protecting
               ┏┓      ┏┓
            ┏┛┻━━━┛┻┓
            ┃      ☃      ┃
            ┃  ┳┛  ┗┳  ┃
            ┃      ┻      ┃
            ┗━┓      ┏━┛
                ┃      ┗━━━┓
                ┃  神兽保佑    ┣┓
                ┃　永无BUG！   ┏┛
                ┗┓┓┏━┳┓┏┛
                  ┃┫┫  ┃┫┫
                  ┗┻┛  ┗┻┛
                  
-------------------------------------------------------------------------------
"""
# 引入数据库游标函数
'''
这两兆的文件处理起来太慢了，每次都是从新使用游标读取 在效率上应该可以优化
这方面需要加强
'''
from colorama import init, Fore, Back, Style
init()# colorama初始化
from collections import Counter
import datetime
# 生成词云图
import jieba
import logging
import os
import webbrowser  # 用来自动打开浏览器页面嘿嘿
from get2db import db_run
from jieba import analyse
# 效率的事情稍 后来转么进行实现 特别是规范化的问题
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import numpy as np
from PIL import Image

LOG_FILENAME_NOTE = "./log/log.txt"
logging.basicConfig(filename=LOG_FILENAME_NOTE, level=logging.INFO)


def log(msg):
    logging.info(str(msg))


from get2db import get2db


class moniter_platform(object):
    def __init__(self):
        # 这个初始化变量还真是有点对 我把这个当做函数公共变量来使用了 不知道设计算不算合理 先用着吧
        self.db_result = self.get_db_reslt()
        self.first_strike_up = ''
        self.sec_strike_up = ''
        self.history_name = []
        self.chat_his = []  # 聊天历史年份
        self.year_time = 2  # 默认时长两年
        self.time_gap = []
        self.sql = 'select * from msg'
        self.count_word = {}
        self.year_list = []
        self.day_dict = {}
        self.row_day_dict = {}
        self.boy_rate_list = []
        self.girl_rate_list = []
        self._first_time = ''
        self._last_time = ''

    def get_db_reslt(self):
        sql = 'select * from msg'
        db = get2db().connect_db()
        cursor = db.cursor()
        cursor.execute(sql)
        check_result = cursor.fetchall()
        return check_result

    def visual_time(self):
        self._first_time = self.db_result[0][3]
        self._last_time = self.db_result[-1][3]
        check_result = self.get_field()
        index_result = dict()
        hour_result = dict()
        for i in check_result:
            # 开始桶排序 取前10字节 的日期
            index_day = str(i)[0:10]
            index_hour = str(i)[11:13]
            count = index_result.get(index_day, 0)
            hour_count = hour_result.get(index_hour, 0)
            if int(count) > 0:
                middle_num = index_result[index_day] + 1
                index_result[index_day] = middle_num
            else:
                index_result[index_day] = 1
            if int(hour_count) > 0:
                middle_hour = hour_result[index_hour] + 1
                hour_result[index_hour] = middle_hour
            else:
                hour_result[index_hour] = 1
        day_list = sorted(self.dict_2_real_list(index_result), key=lambda x: x[1], reverse=True)
        self.day_dict = self.change_day_list(day_list)
        self.row_day_dict = day_list
        hour_list = sorted(self.dict2list(hour_result), key=lambda x: x[1], reverse=True)
        new_day_list = self.dict_tuple_2_json(day_list)
        new_hour_list = self.dict_tuple_2_json(hour_list)
        # 新建转换
        # self.json2file(new_day_list,'day.json')
        self.json2file(new_hour_list, 'hour.js')
        return [new_day_list, new_hour_list]

    '''
    该方法主要用于 将字典 转换为js 可以识别的 json txt
    但是 后续 还需要润色
    '''

    def change_day_list(self, day_list):
        back_dict = dict()
        year_list = []
        for one_day in day_list:
            check_year = one_day[0][0:4]
            if check_year not in year_list:
                year_list.append(check_year)
                back_dict[check_year] = []
            elif check_year in year_list:
                back_dict[check_year].append(one_day)
        '''这个sort一下是为了方便后面calendar排序'''
        # year_list = sorted(year_list)
        # self.year_list = year_list
        return back_dict

    def dict_tuple_2_json(self, dict_tuple):
        back_dict = {}
        x_data = []
        y_data = []
        for i in dict_tuple:
            # 注意： 这里有可能前面字符串截取有问题
            x_data.append(str(i[0]).replace(':', ''))
            y_data.append(i[1])
        back_dict['x_data'] = x_data
        back_dict['y_data'] = y_data
        return back_dict

    def dict2list(self, dic):
        ''' 将字典转化为列表 '''
        keys = dic.keys()
        vals = dic.values()
        lst = [(key, val) for key, val in zip(keys, vals)]
        return lst

    # 这个函数是因为js 没有元组这个数据对象，需要用Python 提前做转换
    def dict_2_real_list(self, dic):
        ''' 将字典转化为列表 注意 内部也是list 不是元组 '''
        keys = dic.keys()
        vals = dic.values()
        lst = [[key, val] for key, val in zip(keys, vals)]
        return lst

    def turn_tuplelist(self, dic1, dic2):
        new_dict = []
        for i in range(0, len(dic1)):
            new_dict.append((dic1[i], dic2[i]))
        return new_dict

    # 获取数据库中字段，默认为获取时间
    # 仅接受 一个condition
    def get_field(self, num=3, time_limit=None, *condition):
        back_result = []
        sql_condition = condition
        # 存在condition where 语句 就重新执行sql 否则就用统一的
        if sql_condition:
            sql_plus = ' where ' + str(sql_condition[0]) + '=' + "'" + str(sql_condition[1]) + "'"
            all_sql = self.sql + sql_plus
            db = get2db().connect_db()
            cursor = db.cursor()
            log(all_sql)
            cursor.execute(all_sql)
            check_result = cursor.fetchall()
        else:
            sql_plus = ''
            check_result = self.db_result

        # 如果db_result为空 就到数据区中取值 否则就用平时已经存储过的值

        for i in check_result:
            if not time_limit:
                back_result.append(i[num])
            else:
                tail_time = datetime.datetime.strptime(time_limit[0], '%Y-%m-%d')
                header_time = datetime.datetime.strptime(time_limit[1], '%Y-%m-%d')
                compare_time = datetime.datetime.strptime(i[3], '%Y-%m-%d %H:%M:%S')
                if compare_time <= header_time and compare_time >= tail_time:
                    back_result.append(i[num])
        return back_result

    # 获取聊天的年份 方便对回复速率进行年份间的评估
    def get_chat_his(self):
        time_data = self.get_field(3)
        chat_his = []
        tail_flag = header_flag = False
        count = 0
        for i in time_data:
            count += 1
            if count == 1 and int(str(i)[5:7]) < 7:
                tail_flag = True
            if count == len(time_data) and int(str(i)[5:7]) > 5:
                header_flag = True
            if str(i)[0:4] not in chat_his:
                chat_his.append(str(i)[0:4])
        # 第一个布尔类型表示最开始年份是否有半年之久
        # 第二个布尔类型表示后续年份超过六个月
        chat_his.append(tail_flag)
        chat_his.append(header_flag)
        self.chat_his = chat_his
        log(chat_his)
        return chat_his

    def get_first_strike(self,time_gap=None):
        appear_name_list = self.get_field(2, time_limit=time_gap)
        mixed_name_dict = Counter(appear_name_list)
        # new_name_dict=dict(mixed_name_dict)
        name_list=sorted(mixed_name_dict.items(), key=lambda d:d[1], reverse = True)
        self.first_strike_up=name_list[0][0]
        self.sec_strike_up=name_list[1][0]
        # reply_data = self.turn_tuplelist(self.get_field(2), self.get_field(3))
        # # 注意 有些msg 第一条是系统信息 会导致倒错
        # self.first_strike_up = reply_data[2][0]
        # if not self.first_strike_up or self.first_strike_up == '' or  self.first_strike_up == '\n':
        #     self.first_strike_up = reply_data[3][0]
        return self.first_strike_up

    def reply_rate(self, interval_time=None):
        reply_data = self.turn_tuplelist(self.get_field(2, interval_time), self.get_field(3, interval_time))
        # 第一次打招呼的人
        first_strike_up = self.get_first_strike(time_gap=interval_time)
        first_gap_list = []
        sec_gap_list = []

        for i in range(0, len(reply_data) - 1):
            # 如果两条中的后一条不是最先打招呼的那人发的
            # if self.sec_strike_up=='':
            if first_strike_up != str(reply_data[i + 1][0]):
                # self.sec_strike_up = str(reply_data[i + 1][0])
                # 对 研究记录对象的 曾用名 进行统计
                filter_name = str(reply_data[i + 1][0]).replace('系统消息', '').replace('用户名未查询到', '')
                if filter_name not in self.history_name and filter_name != '':
                    self.history_name.append(str(reply_data[i + 1][0]))
                # 由于改用sqllite 导致这里时间格式需要再脚本计算修改
                gap2_time = datetime.datetime.strptime(reply_data[i + 1][1], '%Y-%m-%d %H:%M:%S')
                gap1_time = datetime.datetime.strptime(reply_data[i][1], '%Y-%m-%d %H:%M:%S')
                first_gap_time = gap2_time - gap1_time
                first_gap_list.append(first_gap_time)
            elif first_strike_up == str(reply_data[i + 1][0]):
                gap2_time = datetime.datetime.strptime(reply_data[i + 1][1], '%Y-%m-%d %H:%M:%S')
                gap1_time = datetime.datetime.strptime(reply_data[i][1], '%Y-%m-%d %H:%M:%S')
                sec_gap_time = gap2_time - gap1_time

                sec_gap_list.append(sec_gap_time)
        # 这个数据格式还是满奇特的
        first_sum_time = datetime.timedelta(0, 0)
        sec_sum_time = datetime.timedelta(0, 0)
        for i in first_gap_list:
            first_sum_time = first_sum_time + i
        for j in sec_gap_list:
            sec_sum_time = sec_sum_time + j
        first_avg_time = first_sum_time / len(first_gap_list)
        sec_avg_time = sec_sum_time / len(sec_gap_list)
        if interval_time:
            if int(interval_time[1][:4]) - int(interval_time[0][:4]) == 1:
                time_axis = interval_time[0][:4] + '下半年'
            elif int(interval_time[1][:4]) - int(interval_time[0][:4]) == 0:
                time_axis = interval_time[0][:4] + '上半年'
            else:
                time_axis = 'Wrong'
        else:
            time_axis = self.chat_his[0]
        print(self.history_name)
        print(Fore.GREEN + '平均回复' + '【' + self.first_strike_up + '】' + '的时间是：' + str(first_avg_time))
        print(Fore.GREEN + '平均回复' + '【' + self.sec_strike_up + '】' + '的时间是：' + str(sec_avg_time))
        self.year_list.append(time_axis)
        self.boy_rate_list.append(self.change_datetime_formate(first_avg_time))
        self.girl_rate_list.append(self.change_datetime_formate(sec_avg_time))
        return [time_axis, self.change_datetime_formate(first_avg_time), self.change_datetime_formate(sec_avg_time)]

    def change_datetime_formate(self, row_datetime):
        middle_data = str(row_datetime).split(':')
        sum_min = int(middle_data[0]) * 60 + int(middle_data[1])
        return sum_min

    def get_time_gap(self):
        if not self.chat_his:
            self.get_chat_his()
        self.year_time = len(self.chat_his[:-2])

        for year in self.chat_his[:-2]:
            self.time_gap.append(str(year) + '-01-01')
            self.time_gap.append(str(year) + '-06-30')
        # 若存在最初日期大于六月份
        log(self.chat_his)
        if not self.chat_his[-2]:
            self.time_gap = self.time_gap[1:]
        if not self.chat_his[-1]:
            self.time_gap = self.time_gap[:-1]
        log('your time_gap %s' % self.time_gap)
        return self.time_gap

    def get_reply_fluency(self, time_gap=None):
        appear_name_list = self.get_field(2, time_gap)
        fluency_table = Counter(appear_name_list)
        # 这个在time_gap 没修复好之前不能去掉
        first_frequency = fluency_table[self.first_strike_up] / len(appear_name_list)
        sec_frequency = 1 - first_frequency
        first_ratio_reply = first_frequency / sec_frequency
        sec_ratio_reply = sec_frequency / first_frequency
        print(self.first_strike_up + "回复频率为 1: " + "%.2f" % first_ratio_reply)
        print(self.sec_strike_up + "回复频率为 1: " + "%.2f" % sec_ratio_reply)
        onedict = dict()
        secdict = dict()
        back_json = {}
        first_name_fluency = self.first_strike_up + "回复频率"
        sec_name_fluency = self.sec_strike_up + '回复频率'
        onedict["name"] = first_name_fluency
        onedict["value"] = int(first_ratio_reply * 100)
        secdict["name"] = sec_name_fluency
        secdict["value"] = int(sec_ratio_reply * 100)
        back_json['x_data'] = [first_name_fluency, sec_name_fluency]
        back_json['y_data'] = [onedict, secdict]
        self.json2file(back_json, 'reply_ratio.js')
        return back_json

    def get_content_ratio(self, time_gap=None):
        first_content_list = ''.join(self.get_field(1, time_gap, 'qq_user', self.first_strike_up))
        first_content_length = len(first_content_list)
        sec_content_list = ''.join(self.get_field(1, time_gap, 'qq_user', self.sec_strike_up))
        sec_content_length = len(sec_content_list)
        first_ratio_content = first_content_length / sec_content_length
        sec_ratio_content = sec_content_length / first_content_length
        print(self.first_strike_up + "内容回复比率为 1: " + "%.2f" % first_ratio_content)
        print(self.sec_strike_up + "内容回复比率为 1: " + "%.2f" % sec_ratio_content)
        # 这里重新初始化
        onedict = dict()
        secdict = dict()
        back_json = {}
        first_name_content = self.first_strike_up + "内容回复比率"
        sec_name_content = self.sec_strike_up + '内容回复比率'
        onedict["name"] = first_name_content
        onedict["value"] = int(first_ratio_content * 100)
        secdict["name"] = sec_name_content
        secdict["value"] = int(sec_ratio_content * 100)
        back_json['x_data'] = [first_name_content, sec_name_content]
        back_json['y_data'] = [onedict, secdict]
        self.json2file(back_json, 'content_ratio.js')
        return back_json

    # 我发现用jieba 切分词不如他写的 分离tag 方法好用
    def jieba_count_word(self, time_gap=None):
        jieba.set_dictionary('foobar.txt')
        # 有些聊天词语 字典加了也不给划分 因此我在这里强制一下
        jieba.suggest_freq(('会从', '[表情]'))
        msg_list = self.get_field(1, time_gap)
        count_gap_word = {}
        for single_msg in msg_list:
            cut_sentence = jieba.cut(single_msg)
            for word in cut_sentence:
                if not count_gap_word.get(word, None):
                    count_gap_word.setdefault(word, 1)
                if not self.count_word.get(word, None):
                    self.count_word.setdefault(word, 1)
                else:
                    plus_one = count_gap_word[word] + 1
                    fuck_one = self.count_word[word] + 1
                    count_gap_word[word] = plus_one
                    self.count_word[word] = fuck_one
        jieba_count = sorted(self.dict2list(count_gap_word), key=lambda x: x[1], reverse=True)
        return jieba_count

    def json2file(self, dict, filename):
        file_path = os.getcwd() + '\\show\\json\\' + filename
        f = open(file_path, 'w', encoding='utf-8')
        plus_str = 'var ' + str(filename)[:-3] + '='
        row_str = str(dict).replace("'", '"').replace('True', 'true') + ';'
        write_str = plus_str + row_str
        f.write(write_str)
        print(Fore.GREEN + 'Set up %s success' % filename)

    def make_calendar_data(self, time_list=None):
        time_list = self.time_gap
        calendar_list = []
        if len(time_list) < 2:
            range_time = time_list[0][0:4] + '-12-31'
            time_list.append(range_time)
            pinnes_time_list = len(time_list)
        else:
            pinnes_time_list = len(time_list)
        for count in range(pinnes_time_list - 1):
            single_calendar = {}
            my_range = [time_list[count], time_list[count + 1]]
            my_top = 100 + 240 * count
            # 这里防止2016 进行干扰月份判定 所以选择[4:]
            if str(6) in str(time_list[count])[4:]:
                my_formatter = '{start}' + ' 下半年'
            else:
                my_formatter = '{start}' + ' 上半年'
            single_calendar["left"] = "center"
            single_calendar["range"] = my_range
            single_calendar["top"] = my_top
            single_calendar["splitLine"] = {
                "show": True,
                "lineStyle": {
                    "color": '#000',
                    "width": 4,
                    "type": 'solid'
                }}
            single_calendar["yearLabel"] = {
                "formatter": my_formatter,
                "textStyle": {
                    "color": '#fff'
                }
            }
            single_calendar["itemStyle"] = {
                "normal": {
                    "color": '#323c48',
                    "borderWidth": 1,
                    "borderColor": '#111'
                }
            }
            calendar_list.append(single_calendar)
        back_json = {"data": calendar_list}
        my_year_data = self.form_calendar_detail()
        back_json["calendar"] = my_year_data
        self.json2file(back_json, 'calendar.js')
        return calendar_list

    def form_reply_rate_json(self):
        back_json = {}
        # 针对同一年的情况下 我按照对月份进行划分
        new_gap = []
        if len(self.year_list) < 2:
            new_gap.append(self._first_time[0:10])
            first_mounth = int(self._first_time[5:7])
            last_mounth = int(self._last_time[5:7])
            plus_mounth = last_mounth - first_mounth
            for mounth in range(0, plus_mounth):
                middle_mounth = str((int(self._first_time[5:7]) + 1 + mounth))
                if int(middle_mounth) < 10:
                    middle_mounth = '0' + middle_mounth
                later_mounth = str(self._last_time[0:5]) + middle_mounth + self._last_time[7:10]

                new_gap.append(later_mounth)
            count = 0
            for gap in new_gap[:-1]:
                small_gap = [new_gap[count], new_gap[count + 1]]
                self.reply_rate(small_gap)
            back_json['x_data'] = new_gap
        else:
            back_json['x_data'] = self.year_list
        back_json['boy'] = self.boy_rate_list
        back_json['girl'] = self.girl_rate_list
        self.json2file(back_json, 'reply_fluency.js')

    def form_calendar_detail(self):
        # 该函数必须在visual_time方法后运行，在后续初始化函数中必须要进行先调用
        count = -1
        calendar_detail_list = []

        for year in self.year_list:
            first_half_year = {}
            # 新增突出前十二名 的字典
            shine_half_year = {}
            this_year_data = self.day_dict[year[0:4]]
            first_half_year["name"] = '频次'
            shine_half_year["name"] = 'Top 12'
            first_half_year["type"] = 'scatter'
            shine_half_year["type"] = 'effectScatter'
            first_half_year["coordinateSystem"] = 'calendar'
            shine_half_year["coordinateSystem"] = 'calendar'
            first_half_year["data"] = this_year_data

            if len(this_year_data) > 12:
                shine_half_year["data"] = this_year_data[0:12]
            else:
                shine_half_year["data"] = []
            print(shine_half_year)
            count += 1
            first_half_year["calendarIndex"] = count
            shine_half_year["calendarIndex"] = count
            # 这个func 我要用python 重写并输出为好
            first_half_year["symbolSize"] = "function (val) {return val[1] / 50;}"
            shine_half_year["symbolSize"] = "function (val) {return val[1] / 50;}"
            # first_half_year["symbolSize"] = 20
            first_half_year["itemStyle"] = {
                "normal": {
                    "color": '#ddb926'
                }
            }
            shine_half_year["showEffectOn"] = 'render'
            shine_half_year[" rippleEffect"] = {
                "brushType": 'stroke'
            }
            shine_half_year["hoverAnimation"] = True
            shine_half_year["itemStyle"] = {
                "normal": {
                    "color": '#f4e925',
                    "shadowBlur": 10,
                    "shadowColor": '#333'
                }
            }
            shine_half_year["zlevel"] = 1
            calendar_detail_list.append(first_half_year)
            calendar_detail_list.append(shine_half_year)
        self.fuck_pinnes()
        return calendar_detail_list

    def fuck_pinnes(self):
        your_pinnes_size = self.row_day_dict[0][1]
        back_json = {"data": your_pinnes_size}
        self.json2file(back_json, 'little_pinnes.js')

    def show_page(self):
        html_path = os.getcwd() + '\\show\\showtime.html'
        webbrowser.open(html_path)

    def make_tag_pic(self):
        # 获取工作路径
        content = ''.join(self.get_field(num=1))
        # 数量多一点好
        tag_list = jieba.analyse.extract_tags(content,topK=30)
        file_path = os.getcwd()
        print(tag_list)
        # 生成词云图
        wl = ",".join(tag_list)
        foot_path = file_path + '\\show\\font\\造字工房尚黑G0v1常规体.otf'
        save_path = file_path + '\\show\\pic\\ciyun.jpg'
        # 设置背景图片路径
        abel_mask = np.array(Image.open(file_path + '\\show\\ciyun\\background_image\\love .jpg'))

        wc = WordCloud(background_color="white",  # 设置背景颜色
                       mask=abel_mask,  # 设置背景图片
                       max_words=200,  # 设置最大显示的字数
                       # stopwords = "", #设置停用词
                       # 这里注意兼容 linux 版本 以及font 字体
                       font_path=foot_path,
                       # 设置中文字体，使得词云可以显示（词云默认字体是“DroidSansMono.ttf字体库”，不支持中文）
                       max_font_size=100,  # 设置字体最大值
                       random_state=30,  # 设置有多少种随机生成状态，即有多少种配色方案
                       scale=1.5  # 设置保存的词云图尺寸大小
                       )

        myword = wc.generate(wl)  # 生成词云
        # 这里将图片存放到pic 文件夹里面
        wc.to_file(save_path)
        # 展示词云图
        plt.title("LoveTime")
        plt.imshow(myword)
        plt.axis("off")  # figure（显示窗口）默认是带axis（坐标尺）的，如果没有需要，我们可以关掉

    def run(self):
        db_run()
        count = 0
        self.__init__()
        self.get_time_gap()
        print(self.time_gap[:-1])
        if len(self.time_gap) < 3:
            self.reply_rate()
            self.get_reply_fluency()
            self.get_content_ratio()
            # self.jieba_count_word()
        else:
            for gap in self.time_gap[:-1]:
                print(self.time_gap[count + 1])
                small_gap = [self.time_gap[count], self.time_gap[count + 1]]
                self.reply_rate(small_gap)
                self.get_reply_fluency(small_gap)
                self.get_content_ratio(small_gap)
            # self.jieba_count_word(small_gap)
                count += 1
        self.visual_time()
        self.get_reply_fluency()
        self.get_content_ratio()
        self.make_calendar_data()
        self.form_calendar_detail()
        self.form_reply_rate_json()
        self.make_tag_pic()
        self.show_page()


# 这些复杂的函数 到时还是写一个unittest
'''这个启动太繁琐以后要做一个run 函数'''
if __name__ == "__main__":
    moniter = moniter_platform()
    moniter.run()
