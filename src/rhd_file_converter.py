#V1.0: basic function(saved as mat)
#V2.0: gui, change output format to nex/nex5
#V2.1: 噪声段去除，弹窗报错
#V2.2: Cfg save
#V3: ofb script gen
#chig 

import sys, os, re
import numpy as np
from csv import DictReader
import json
from time import mktime, strptime, strftime, localtime
from time import strptime

import tkinter as tk
from tkinter import ttk
from tkinter.filedialog import askdirectory
from tkinter.messagebox import showinfo, showerror

from load_intan_rhd_format import read_data

from NexFileData import *
import NexFileWriters

from logo import *

def save_log(s):
    t = strftime('%Y-%m-%d %X', localtime())
    print ('%s--%s'%(t,s))

def get_rhds(info):
    files = os.listdir(info['db'])
    file_list = []
    for file in files:
        reobj = re.search(r'.*_(?P<year>\d{2})(?P<month>\d{2})(?P<date>\d{2})_(?P<hour>\d{2})(?P<minute>\d{2})(?P<second>\d{2})\.rhd', file)
        if reobj:
            td = reobj.groupdict()
            ts = "20"+td["year"]+" "+td["month"]+" "+td["date"]+" "+td["hour"]+" "+td["minute"]+" "+td["second"]
            timestamp = mktime(strptime(ts,"%Y %m %d %H %M %S")) 
            file_list.append((info['db']+"\\"+file, timestamp))
    file_list.sort(key=lambda x:x[1])
    if len(file_list)==0:
        showerror(title = "错误", message = "输入文件夹中没有rhd文件")
        return []
    elif len(file_list)>1:
        len_per_file = file_list[1][1] - file_list[0][1]
        for i in range(len(file_list)-1):
            if not file_list[i+1][1] - file_list[i][1] == len_per_file:
                showerror(title = "错误", message = "输入文件夹包含非连续记录的多个rhd文件")
                return []
    save_log("Get "+str(len(file_list))+" rhd files in total. Start parsing data.\n" )
    progressbar_update(0)
    return file_list

def decode_rhds(file_list, info):
    data_list = []
    total_time = 0
    sample_rate_list = []
    port_list = []
    #disable_ch = list(range(128))
    work_ch = []
    imp = []
    for f in file_list:
        file_path = f[0]
        save_log("Parsing data from "+file_path+" ...")
        data, record_time, sample_rate=read_data(file_path)
        if not len(port_list):
            for ch_info in data['amplifier_channels']:
                port_list.append(ch_info['port_prefix'])
                work_ch.append(ch_info['native_order'])
                #disable_ch.remove(ch_info['native_order'])
                imp.append(ch_info['electrode_impedance_magnitude'])
            #disable_ch.sort()
            work_ch.sort()
            #for c in disable_ch:
                #imp.insert(c, 0)
            if len(set(port_list)) > 1:
                showerror(title = "错误", message = "当前版本暂不支持记录多个port的rhd文件")
                return []
        sample_rate_list.append(sample_rate)
        total_time += record_time
        data_list.append(data['amplifier_data'])
    if len(set(sample_rate_list)) > 1:
        showerror(title = "错误", message = "rhd文件的采样率不同")
        return []
    print("")
    save_log("Parsing complete. Get "+str(total_time)+" seconds data in total with sample rate of "+str(sample_rate_list[0]/1000)+" kHz.\n")
    progressbar_update(5)
    info['imp'] = imp
    info['sample_rate'] = sample_rate_list[0]
    info['work_ch'] = work_ch
    #info['disable_ch'] = disable_ch
    return data_list

def data_merge(data_list, info):
    data = data_list[0]
    del data_list[0]
    while len(data_list)>0:
        data = np.append(data, data_list[0], axis=1)
        del data_list[0]
    
    ch, length = data.shape
    delete_col = []
    for dl in info['delete_list']:
        start = dl[0]*int(info['sample_rate'])
        if start >= length:
            continue
        if dl[1] == 'end':
            end = length
        else:
            end = dl[1]*int(info['sample_rate'])
        if end > length:
            end = length
        delete_col += list(range(start, end))
    delete_col = list(set(delete_col))
    delete_col.sort()
    data = np.delete(data, delete_col, axis=1)

    #ch, length = data.shape
    #zero_ch = np.array([0]*length)
    #for c in info['disable_ch']:
        #data = np.insert(data, c, zero_ch, axis=0) 
    progressbar_update(20)
    return data

def imp_decode(data, info):
    if not info['open_en']:
        info['short_ch'] = []
        return data
    files = os.listdir(info['db'])
    file_list = []
    for file in files:  
        if re.search(r'.*\.csv', file):
            file_list.append(file)
    if len(file_list)>1:
        showerror(title = "错误", message = "输入文件夹中有多个阻抗csv文件")
        return 1
    elif len(file_list) == 1:
        imp_file_path = info['db']+"\\"+file_list[0]
        save_log("Parsing impedance from: "+imp_file_path+"...")
        with open(imp_file_path, 'r') as impfile:
            reader = DictReader(impfile)
            info['imp'] = [eval(row['Impedance Magnitude at 1000 Hz (ohms)']) for row in reader]
    elif len(file_list) == 0:
        save_log("Do not get impedance file, use the impedance stored in rhd file")
    
    info['short_ch'] = []
    for i in range(len(info['imp'])):
        #if i in info['disable_ch']:
            #save_log ("Channel "+str(i)+" is disable")
        if info['imp'][i] > info['threshold']:
            save_log ("Channel "+str(i)+" is opening. Impedance: "+str(info['imp'][i]/1e6)+" MΩ.")
            ch_idx = info['work_ch'].index(i)
            info['work_ch'].remove(i)
            data = np.delete(data, ch_idx, axis=0)
            #info['disable_ch'].append(i)
        elif info['imp'][i] < 10000:
            save_log("Impedance of Channel "+str(i)+" is too low. Impedance: "+str(info['imp'][i]/1e6)+" MΩ.")
            info['short_ch'].append(i)
    print("")
    #info['disable_ch'] = list(set(info['disable_ch']))
    #info['disable_ch'].sort()
    return data

def ref_process (data, info):    
    #imp_process = np.array([[0] if i in info['disable_ch'] else [1] for i in range(128)])
    #data = imp_process*data
    if info['ref_en']:
        ref = data.mean(axis=0)
        data -= ref
    return data

def save_nex (data, info):
    save_log ("Saving data into file, may take several minutes. Please wait ...\n")
    if info['file_format']:
        f_name = info['file_name'] + ".nex5"
    else:
        f_name = info['file_name'] + ".nex"
    info['nex_name'] = f_name
    if os.path.exists(f_name):
        os.remove(f_name)
    ch, lenth = data.shape
    file_abspath = os.path.abspath(f_name)
    fd = FileData()
    fd.TimestampFrequency = info['sample_rate']
    fd.Events.append(Event('StartStop', [0, (lenth-1)/info['sample_rate']]))
    fd.Intervals.append(Interval('AllFile', [0], [(lenth-1)/info['sample_rate']]))
    for c in range(ch):
        #if c in info['disable_ch']:
            #continue
        if c in info['short_ch']:
            c_name = 'ch'+str(info['work_ch'][c])+'(short)'
        else:
            c_name = 'ch'+str(info['work_ch'][c])
        fd.Continuous.append(Continuous(c_name, info['sample_rate'], [0], [0], data[c].tolist()))
        p_value = 20+int(c/128*80)
        progressbar_update(p_value)
    if not info['file_format']:
        writerNex = NexFileWriters.NexFileWriter()
        writerNex.WriteDataToNexFile(fd, f_name)
    else:
        writerNex5 = NexFileWriters.Nex5FileWriter()
        writerNex5.WriteDataToNex5File(fd, f_name)
    progressbar_update(100)
    save_log ("Process complete.")
    save_log ("Location of output mat file: "+str(file_abspath))

def gen_ofb(ofb_info):
    pre_name = ofb_info['file_name'] + '_pre.ofb'
    post_name = ofb_info['file_name'] + '_post.ofb'
    with open(pre_name, "w") as f:
        f.write("File " + ofb_info['nex_name'] + "\n")
        if ofb_info['filter_en']:
            f.write("ForEachChannel Filter\n")
        if ofb_info['detect_en']:
            f.write("ForEachChannel Detect\n")
        if ofb_info['sort_en']:
            f.write("ForEachChannel " + ofb_info['sort_type'] + "\n")

        if ofb_info['filter_en']:
            f.write("Set FilterFreq " + ofb_info['filter_cutoff'] + "\n")
            f.write("Set FilterType " + ofb_info['filter_type'] + "\n")
            f.write("Set FilterPoles " + ofb_info['filter_pole'] + "\n")

        if ofb_info['align_en']:
            f.write("Set AlignDuringDetect "+"1"+"\n")
            f.write("Set AlignType "+"4"+"\n")

        if ofb_info['detect_en']:
            f.write("Set DetectMicrovolts " + ofb_info['detect_threshold'] + "\n")

        f.write("Set FeatureX 0\n")
        f.write("Set FeatureY 1\n")
        f.write("Set FeatureZ 2\n")
        f.write("Process\n")
    with open(post_name, "w") as f:
        f.write("ForEachFile ExportToNex\n")
        f.write("Set SaveNexCont 1\n")
        f.write("Set SaveNexProcessedCont 1\n")
        f.write("Set SaveNexWaveforms 1\n")
        f.write("Set SaveNexUnsorted 0\n")
        f.write("Set SaveNexUnitTemplates 0\n")
        f.write("Process\n")

def db_select():
    database.set('')
    database_name = askdirectory()
    if database_name:
        database.set(database_name.replace('/','\\'))

def delete_help():
    help_info = "用于删除小鼠运动等导致的某几段噪声，然后将剩余信号段重新拼接\n"
    help_info += "输入格式：(a,b)表示要删除的一段信号，a为起始时间，b为结束时间，$代表信号最后。多段信号之间用分号隔开\n"
    help_info += "示例：(8,10);(58,$)代表删除8-10秒和58秒开始到数据结束的两段数据\n"
    help_info += "使用英文半角标点符号！！时间点当前仅支持整数\n注意拼接点处可能会出现信号突变"
    showinfo(title = "段落裁剪说明", message = help_info)

def run():
    if not database:
        showerror(title = "错误", message = "必须指定输入数据文件夹")
        return 1
    
    cur_path = os.getcwd()
    log_file = open(cur_path+'\\Rhd_File_Converter.log', 'a')
    tmp = sys.stdout
    #sys.stdout = log_file

    print("")
    print("="*80)
    save_log ("Start a new converter")
    info = {}
    info['db'] = database.get().replace("/","\\")
    info['threshold'] = int(threshold.get())*1000000
    info['open_en'] = open_en.get()
    info['ref_en'] = ref_en.get()
    info['delete_en'] = delete_en.get()
    info['align_en'] =align_en.get()

    delete_list = []
    if info['delete_en']:
        d_string = delete_string.get().replace(' ','').replace('\n','').replace('\r','')
        d_strings = d_string.split(';')    
        for s in d_strings:
            reobj = re.search(r'^\((?P<start>\d+),(?P<end>\d+)\)$', s)
            reobj_end = re.search(r'^\((?P<start>\d+),(?P<end>\$)\)$', s)
            if reobj:
                rd = reobj.groupdict()
                delete_list.append((int(rd['start']), int(rd['end'])))
            elif reobj_end:
                rd = reobj_end.groupdict()
                delete_list.append((int(rd['start']), 'end'))
            else:
                showerror(title = "错误", message = "噪声段删除：输入格式错误")
                log_file.close()
                sys.stdout = tmp
                return 1
    info['delete_list'] = delete_list
    info['file_format'] = file_format.get()
    info['file_name'] = os.path.join(info['db'], file_name.get())

    file_list = get_rhds(info)
    if len(file_list) == 0:
        log_file.close()
        sys.stdout = tmp
        return 1
    
    data_list = decode_rhds(file_list, info)
    if len(data_list) == 0:
        log_file.close()
        sys.stdout = tmp
        return 1

    data = data_merge(data_list, info)
    data = imp_decode(data, info)
    if not (type(data) is np.ndarray):
        print("error")
        print(type(data))
        log_file.close()
        sys.stdout = tmp
        return 1

    data = ref_process(data, info)
    save_nex(data, info)    

    if gen_ofb_en.get():
        ofb_info = {}
        ofb_info['file_name'] = info['file_name']
        ofb_info['nex_name'] = info['nex_name']
        ofb_info['filter_en'] = filter_en.get()
        ofb_info['align_en'] =align_en.get()
        if ofb_info['filter_en']:
            ofb_info['filter_pole'] = filter_pole.get()
            ofb_info['filter_cutoff'] = filter_cutoff.get()
            ofb_info['filter_type'] = filter_type.get()
        ofb_info['detect_en'] = detect_en.get()
        if ofb_info['detect_en']:
            ofb_info['detect_threshold'] = detect_threshold.get()
        ofb_info['sort_en'] = sort_en.get()
        if ofb_info['sort_en']:
            ofb_info['sort_type'] = sort_type.get()
        gen_ofb(ofb_info)

    log_file.close()
    sys.stdout = tmp  
    showinfo(title = "", message = "处理完成") 
    return data

def save_cfg():
    cfg = {}
    cfg['ref_en'] = ref_en.get()
    cfg['open_en'] = open_en.get()
    cfg['threshold'] = threshold.get()
    cfg['file_format'] = file_format.get()
    cfg['gen_ofb_en'] = gen_ofb_en.get()
    cfg['filter_en'] = filter_en.get()
    cfg['filter_cutoff'] = filter_cutoff.get()
    cfg['filter_type'] = filter_type.get()
    cfg['filter_pole'] = filter_pole.get()
    cfg['detect_en'] = detect_en.get()
    cfg['detect_threshold'] = detect_threshold.get()
    cfg['sort_en'] = sort_en.get()
    cfg['sort_type'] = sort_type.get()
    cfg['align_en'] = align_en.get()
    cur_path = os.getcwd()
    with open(cur_path+'\\OfflineSorter_Helper_Config.json','w') as cfg_f:
        json.dump(cfg, cfg_f, indent=4)
    showinfo(title="", message="配置保存完成")

def progressbar_update(value):
    p_string.set("%3d"%(value)+"%")
    p_lable.config(text=p_string.get())
    progressbar['value'] = value
    root.update()

def init():
    cur_path = os.getcwd()
    if not os.path.exists(cur_path+'\\OfflineSorter_Helper_Config.json'):
        threshold.set(2)
        file_name.set('out')
        return 
    with open(cur_path+'\\OfflineSorter_Helper_Config.json','r') as cfg_f:
        cfg = json.load(cfg_f)
    ref_en.set(cfg['ref_en'])
    open_en.set(cfg['open_en'])
    threshold.set(cfg['threshold'])
    file_format.set(cfg['file_format'])
    file_name.set('out')
    gen_ofb_en.set(cfg['gen_ofb_en'])
    filter_en.set(cfg['filter_en'])
    filter_cutoff.set(cfg['filter_cutoff'])
    filter_pole.set(cfg['filter_pole'])
    filter_type.set(cfg['filter_type'])
    detect_en.set(cfg['detect_en'])
    detect_threshold.set(cfg['detect_threshold'])
    sort_en.set(cfg['sort_en'])
    sort_type.set(cfg['sort_type'])
    align_en.set(cfg['align_en'])


if __name__ == '__main__':
    root = tk.Tk()
    root.title('OfflineSorter Helper V3')
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw-315) / 2
    y = (sh-330) / 2
    root.geometry('315x330+%d+%d'%(x,y))
    root.resizable(False, False)

    database = tk.StringVar()
    tk.Entry(root, textvariable=database, width=33).grid(row=0, column=0, sticky='w', columnspan=3, padx=5)
    tk.Button(root, text='选择数据', pady=0, font=('微软雅黑', 10), command=db_select).grid(row=0, column=3, sticky='w')

    ref_en = tk.IntVar()
    tk.Checkbutton(root, text="去均值",font=('微软雅黑', 10),variable = ref_en,onvalue=1,offvalue=0).grid(row=1, column=0, sticky='w')

    open_en = tk.IntVar()
    tk.Checkbutton(root, text="阻抗筛选",font=('微软雅黑', 10),variable = open_en,onvalue=1,offvalue=0).grid(row=1, column=1, sticky='e')
    threshold = tk.StringVar()    
    tk.Label(root, text='阈值(MΩ)', font=('微软雅黑', 10)).grid(row=1, column=2, sticky='e')
    tk.Entry(root, textvariable=threshold, width=5).grid(row=1, column=3, sticky='w')

    delete_en = tk.IntVar()
    tk.Checkbutton(root, text="裁剪",font=('微软雅黑', 10),variable = delete_en,onvalue=1,offvalue=0).grid(row=2, column=0, sticky='w')
    delete_string = tk.StringVar()
    tk.Entry(root, textvariable=delete_string, width=20).grid(row=2, column=1, columnspan=2, sticky='w')
    tk.Button(root, text='?', width=1, pady=0, font=('微软雅黑', 8, 'bold'), command=delete_help).grid(row=2, column=0, sticky='e', padx=5)

    tk.Label(root, text='输出文件格式', font=('微软雅黑', 10)).grid(row=3, column=0, sticky='w')
    file_format = tk.IntVar()
    tk.Radiobutton(root, text="nex",font=('微软雅黑', 10),variable=file_format, value=0).grid(row=3, column=1, sticky='w')
    tk.Radiobutton(root, text="nex5",font=('微软雅黑', 10),variable=file_format, value=1).grid(row=3, column=2, sticky='w')
    tk.Label(root, text='输出文件名', font=('微软雅黑', 10)).grid(row=4, column=0, sticky='w')
    file_name = tk.StringVar()
    tk.Entry(root, textvariable=file_name, width=20).grid(row=4, column=1, columnspan=2, sticky='w')

    gen_ofb_en = tk.IntVar()
    tk.Checkbutton(root, text="生成OfflineSort自动化处理脚本（需License）",font=('微软雅黑', 10),variable = gen_ofb_en,onvalue=1,offvalue=0).grid(row=5, column=0, sticky='w', columnspan=4)

    filter_en = tk.IntVar()
    tk.Checkbutton(root, text='高通滤波', font=('微软雅黑', 10),variable = filter_en,onvalue=1,offvalue=0).grid(row=6, column=0, sticky='w')
    tk.Label(root, text='滤波器类型', font=('微软雅黑', 10)).grid(row=6, column=1, sticky='w')
    filter_type = ttk.Combobox(root, width=10)
    filter_type['value'] = ['Butterworth','Bessel','Elliptic']
    filter_type.grid(row=6, column=2, sticky='w', columnspan=2)
    tk.Label(root, text='滤波截止频率', font=('微软雅黑', 10)).grid(row=7, column=0, sticky='w')
    filter_cutoff = tk.StringVar()
    tk.Entry(root, textvariable=filter_cutoff, width=8).grid(row=7, column=1, sticky='w')
    tk.Label(root, text='Hz', font=('微软雅黑', 10)).grid(row=7, column=1, sticky='e')
    tk.Label(root, text='滤波器阶数', font=('微软雅黑', 10)).grid(row=7, column=2, sticky='w')
    filter_pole = ttk.Combobox(root, width=5)
    filter_pole['value'] = [2,4,6,8,10,12]
    filter_pole.grid(row=7, column=3, sticky='w')

    detect_en = tk.IntVar()
    tk.Checkbutton(root, text='尖峰检测', font=('微软雅黑', 10),variable = detect_en,onvalue=1,offvalue=0).grid(row=8, column=0, sticky='w')
    tk.Label(root, text='阈值', font=('微软雅黑', 10)).grid(row=8, column=1, sticky='w')
    detect_threshold = tk.StringVar()
    tk.Entry(root, textvariable=detect_threshold, width=6).grid(row=8, column=1, sticky='e')
    tk.Label(root, text='μV', font=('微软雅黑', 10)).grid(row=8, column=2, sticky='w')

    sort_en = tk.IntVar()
    tk.Checkbutton(root, text='尖峰聚类', font=('微软雅黑', 10),variable = sort_en,onvalue=1,offvalue=0).grid(row=9, column=0, sticky='w')
    tk.Label(root, text='聚类方法', font=('微软雅黑', 10)).grid(row=9, column=1, sticky='w')
    sort_type = ttk.Combobox(root, width=11)
    sort_type['value'] = ['ValleySeek2d', 'ValleySeek3d', 'TDist2d', 'TDist3d']
    sort_type.grid(row=9, column=1, columnspan=2,sticky='e')

    align_en = tk.IntVar()
    tk.Checkbutton(root, text='对齐', font=('微软雅黑', 10),variable = align_en,onvalue=1,offvalue=0).grid(row=8, column=3, sticky='w')

    progressbar = ttk.Progressbar(root, length = 120)
    progressbar.grid(row=10, column=0, columnspan=2, sticky='w', padx=5)
    p_string = tk.StringVar()
    p_string.set('  0%')
    p_lable = tk.Label(root, text=p_string.get(),font=('微软雅黑', 10))
    p_lable.grid(row=10, column=1, sticky='e')
    tk.Button(root, text='开始处理', pady=0, font=('微软雅黑', 10), command=run).grid(row=10, column=3)
    tk.Button(root, text='保存配置', pady=0, font=('微软雅黑', 10), command=save_cfg).grid(row=10, column=2, sticky='e',padx=5) 

    pic = tk.PhotoImage(data=logo, width=50, height=80)
    tk.Label(root, image=pic).grid(row=2, column=3, rowspan=3,sticky='wn') 

    init()  
    root.mainloop()
    