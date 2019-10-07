#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import textwrap
from tkinter import *
from tkinter import scrolledtext
from tkinter import filedialog
from tkinter.ttk import *
from heval import human
from heval import abg
from heval import electrolytes


__helptext__ = """\
Введите пол и рост — этого достаточно для большей части антропометрических \
расчётов. Идеальный вес (IBW) рассчитывается по росту и полу автоматически. \
Снимите галочку 'Use IBW' и введите реальный вес, если знаете его.

Мгновенно доступны: IBW, BSA, BMI, объёмы вентиляции, суточная потребность \
в энергии и жидкости, диурез, дозировки ЛС etc.

При наведении курсора на поле ввода появляется всплывающая подсказка.

""" + human.__abbr__

__about__ = """\
Программа медицинская, поэтому состоит из допущений чуть менее чем полностью. \
Не используйте лекарственное средство, если не читали его инструкцию.

Written by Eugene Dvoretsky 2016-2019. Check source code for references and formulas.

Heval is a free software and licensed under the terms of GNU General Public License version 3.
"""


class MainWindow(Frame):
    def __init__(self, parent=None, *args, **kwargs):
        super(MainWindow, self).__init__(parent, *args, **kwargs)
        self.parent = parent
        self.parent.title("Heval — a human evaluator")
        self.parent.geometry("600x590")
        self.parent.bind('<Escape>', lambda e: self.parent.destroy())
        self.parent.style = Style()
        self.parent.style.theme_use('clam')  # ('clam', 'alt', 'default', 'classic')
        self.bind_all('<F1>', lambda e: HelpWindow(self.parent))
        # self.bind('<r>', lambda e: self.set_input_defaults())
        # self.bind('<Control-s>', lambda e: self.save_text())
        # self.bind('<Control-a>', lambda e: self.select_all())
        # self.bind('<Control-c>', lambda e: self.copy_text())

        menubar = Menu(self.parent)
        menu_file = Menu(menubar, tearoff=0)
        # menu_file.add_command(label="Reset values", command=self.set_input_defaults, accelerator="R")
        # menu_file.add_command(label="Save text...", command=self.save_text, accelerator="Ctrl+S")
        menu_file.add_command(label="Exit", command=self.parent.destroy, accelerator="Esc")
        menubar.add_cascade(label="File", menu=menu_file)
        menu_about = Menu(menubar, tearoff=0)
        menu_about.add_command(label="Help", command=lambda: HelpWindow(self.parent), accelerator="F1")
        menu_about.add_command(label="About...", command=lambda: AboutWindow(self.parent))
        menubar.add_cascade(label="Help", menu=menu_about)
        self.parent['menu'] = menubar

        self.HBody = human.HumanBodyModel()

        nb = Notebook(self)
        self.create_input()
        self.set_input_defaults()
        self.MText = MainText(nb, self.HBody)
        self.CElectrolytes = CalcElectrolytes(nb, self.HBody)
        self.CGFR = CalcGFR(nb, self.HBody)
        nb.add(self.MText, text='Human')
        nb.add(self.CElectrolytes, text="ABG & Electrolytes")
        nb.add(self.CGFR, text='eGFR')
        nb.pack(expand=True, fill=BOTH)  # BOTH looks less ugly under Windows

        self.parent.bind('<Alt-KeyPress-1>', lambda e: nb.select(0))
        self.parent.bind('<Alt-KeyPress-2>', lambda e: nb.select(1))
        self.parent.bind('<Alt-KeyPress-3>', lambda e: nb.select(2))
        self.bind_all('<<HumanModelChanged>>', self.MText.print)
        self.bind_all('<<HumanModelChanged>>', self.CElectrolytes.print, add='+')
        self.bind_all('<<HumanModelChanged>>', self.CGFR.print, add='+')

        # self.statusbar_str = StringVar()
        # self.statusbar_str.set("Hello world!")
        # statusbar = Label(self, textvariable=self.statusbar_str, relief=SUNKEN, anchor=W)
        # statusbar.pack(side=BOTTOM, fill=X)

    def create_input(self):
        """One row of input widgets."""
        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)
        Label(fr_entry, text='Sex').pack(side=LEFT)
        self.ctl_sex = Combobox(fr_entry, values=['Male', 'Female', 'Paed'], width=7)
        self.ctl_sex.bind("<<ComboboxSelected>>", self.set_model_sex)
        self.ctl_sex.pack(side=LEFT)
        CreateToolTip(self.ctl_sex, "Age and sex selector. Calculations quite differ for adults and infants")

        Label(fr_entry, text='Height, cm').pack(side=LEFT)
        self.ctl_height = Spinbox(fr_entry, width=3, from_=1, to=500, command=self.set_model_height)
        self.ctl_height.bind("<Return>", self.set_model_height)
        self.ctl_height.pack(side=LEFT)
        CreateToolTip(self.ctl_height, "Height highly correlates with age, ideal body weight and body surface area")

        self.var_use_ibw = IntVar()  # No real body weight
        self.var_use_ibw.set(1)
        self.ctl_use_ibw_cb = Checkbutton(fr_entry, variable=self.var_use_ibw, onvalue=1, offvalue=0, text="Use IBW", command=self.set_model_use_ibw)
        self.ctl_use_ibw_cb.pack(side=LEFT)
        CreateToolTip(self.ctl_use_ibw_cb, "Estimate ideal body weight from height")

        self.lbl_weight = Label(fr_entry, text='Weight, kg')
        self.lbl_weight.pack(side=LEFT)
        self.ctl_weight = Spinbox(fr_entry, width=4, from_=1, to=500,
            format='%.1f', increment=1, command=self.set_model_weight)
        self.ctl_weight.bind("<Return>", self.set_model_weight)
        self.ctl_weight.pack(side=LEFT)
        CreateToolTip(self.ctl_weight, "Real body weight")

        Label(fr_entry, text='Body temp, °C').pack(side=LEFT)
        self.ctl_sbx_temp = Spinbox(fr_entry, width=4, from_=0.0, to=50.0,
            format='%.1f', increment=0.1, command=self.set_model_body_temp)
        self.ctl_sbx_temp.bind("<Return>", self.set_model_body_temp)
        self.ctl_sbx_temp.pack(side=LEFT)
        CreateToolTip(self.ctl_sbx_temp, "Axillary temperature, used for perspiration evaluation")

        reset = Button(fr_entry, text="Reset", command=self.set_input_defaults)
        reset.pack(side=LEFT)
        CreateToolTip(reset, "Drop changes for sex, height, real body weight, temp")

    def set_input_defaults(self, event=None):
        self.ctl_sex.current(0)
        self.set_model_sex()

        self.ctl_height.delete(0, END)
        self.ctl_height.insert(0, 177)  # cm
        self.set_model_height()

        # Can't change widget value while it being disabled, so here is a trick
        self.ctl_weight['state'] = NORMAL
        self.ctl_weight.delete(0, END)
        self.ctl_weight.insert(0, 69.0)  # kg
        self.ctl_weight['state'] = self.lbl_weight['state']
        self.set_model_weight()

        self.var_use_ibw.set(1)
        self.set_model_use_ibw()

        self.ctl_sbx_temp.delete(0, END)
        self.ctl_sbx_temp.insert(0, 36.6)  # celsus degrees
        self.set_model_body_temp()

    def set_model_sex(self, event=None):
        self.HBody.sex = self.ctl_sex.get().lower()
        self.event_generate("<<HumanModelChanged>>")

    def set_model_height(self, event=None):
        self.HBody.height = float(self.ctl_height.get()) / 100
        if self.HBody.use_ibw:
            self.ctl_weight['state'] = NORMAL
            self.ctl_weight.delete(0, END)
            self.ctl_weight.insert(0, round(self.HBody.weight, 1))
            self.ctl_weight['state'] = self.lbl_weight['state']
        self.event_generate("<<HumanModelChanged>>")

    def set_model_weight(self, event=None):
        self.HBody.weight = float(self.ctl_weight.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_body_temp(self, event=None):
        self.HBody.body_temp = float(self.ctl_sbx_temp.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_use_ibw(self, event=None):
        if self.var_use_ibw.get() == 0:
            self.HBody.use_ibw = False
            self.lbl_weight['state'] = NORMAL
            self.ctl_weight['state'] = NORMAL
        else:
            self.HBody.use_ibw = True
            self.ctl_weight.delete(0, END)
            self.ctl_weight.insert(0, round(self.HBody.weight, 1))
            self.ctl_weight['state'] = DISABLED
            self.lbl_weight['state'] = DISABLED
        self.event_generate("<<HumanModelChanged>>")


class HelpWindow(Toplevel):
    def __init__(self, parent=None):
        super(HelpWindow, self).__init__(parent)
        self.parent = parent
        x = self.parent.winfo_x()
        y = self.parent.winfo_y()
        self.geometry("+{:.0f}+{:.0f}".format(x + 50, y + 100))
        self.title('Help')

        self.lbl = Label(self, text=__helptext__, wraplength=500, padding=8)
        self.lbl.pack(expand=True, fill=BOTH)

        self.ctl_frame = Frame(self, padding=8)
        self.ctl_btn_close = Button(self.ctl_frame, text="Close", command=self.destroy)
        self.ctl_btn_close.pack(side=RIGHT)
        self.ctl_frame.pack(expand=True, fill=BOTH)
        self.bind('<Escape>', lambda e: self.destroy())
        self.focus_set()


class AboutWindow(Toplevel):
    def __init__(self, parent=None):
        super(AboutWindow, self).__init__(parent)
        self.parent = parent
        x = self.parent.winfo_x()
        y = self.parent.winfo_y()
        self.geometry("+{:.0f}+{:.0f}".format(x + 50, y + 100))
        self.title('About')

        abouttext = __about__ + "And remember: {}".format(
            random.choice(electrolytes.__EASTER_TEXT__))
        self.lbl = Label(self, text=abouttext, wraplength=500, padding=8)
        self.lbl.pack(expand=True, fill=BOTH)

        self.ctl_frame = Frame(self, padding=8)
        self.ctl_btn_website = Button(self.ctl_frame, text="Visit website", command=self.visit_website)
        self.ctl_btn_close = Button(self.ctl_frame, text="Close", command=self.destroy)
        self.ctl_btn_close.pack(side=RIGHT)
        self.ctl_btn_website.pack(side=RIGHT)
        self.ctl_frame.pack(expand=True, fill=BOTH)
        self.bind('<Escape>', lambda e: self.destroy())
        self.focus_set()

    def visit_website(self, event=None):
        import webbrowser
        webbrowser.open_new_tab("https://github.com/radioxoma/heval")


class TextView(Frame):
    def __init__(self, parent=None):
        super(TextView, self).__init__(parent)
        self.parent = parent

        frm_txt = Frame(self, width=450, height=300)
        frm_txt.pack(expand=True, fill=BOTH)
        frm_txt.grid_propagate(False)  # ensure a consistent GUI size
        frm_txt.grid_rowconfigure(0, weight=1)
        frm_txt.grid_columnconfigure(0, weight=1) # implement stretchability

        self.txt = Text(frm_txt, borderwidth=1, relief="sunken")
        self.txt.config(font=("consolas", 10), undo=True, wrap='word')
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Create a Scrollbar and associate it with txt
        scrollb = Scrollbar(frm_txt, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky='nsew')
        self.txt['yscrollcommand'] = scrollb.set

    def set_text(self, text):
        """Replace current text."""
        self.txt['state'] = NORMAL
        self.txt.delete(1.0, END)
        self.txt.insert(END, text)
        self.txt['state'] = DISABLED

    # def save_text(self):
    #     dst_filepath = filedialog.asksaveasfilename(
    #         title='Save text output',
    #         filetypes=[('Plain text', '.txt'), ('All files', '*')],
    #         defaultextension='.txt',
    #         initialfile="Patient_{}-{}.txt".format(self.ctl_height.get(), self.ctl_weight.get()))
    #     if dst_filepath:
    #         self.txt['state'] = NORMAL
    #         try:
    #             with open(dst_filepath, mode='w') as f:
    #                 f.write(self.txt.get(1.0, "end-1c"))
    #         except Exception as e:
    #             raise
    #         finally:
    #             self.txt['state'] = DISABLED

    def select_all(self):
        self.txt.tag_add(SEL, "1.0", END)
        self.txt.mark_set(INSERT, "1.0")
        self.txt.see(INSERT)
        return 'break'


class TextView2(scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        super(TextView2, self).__init__(*args, **kwargs)
        self.config(font=('consolas', 10), wrap='word')

        self.popup_menu = Menu(self, tearoff=False)
        self.popup_menu.add_command(label="Copy all", command=self.copy_all)
        self.bind("<ButtonRelease-3>", self.popup)

    def set_text(self, text):
        """Replace current text."""
        self['state'] = NORMAL
        self.delete(1.0, END)
        self.insert(END, text)
        self['state'] = DISABLED

    def copy_all(self, event=None):
        self.clipboard_clear()
        text = self.get(1.0, END)
        self.clipboard_append(text)

    def popup(self, event):
        self.popup_menu.tk_popup(event.x_root, event.y_root)


class MainText(Frame):
    def __init__(self, parent, human_model):
        super(MainText, self).__init__(parent)
        self.parent = parent
        self.human_model = human_model

        self.TxtView = TextView2(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.TxtView.set_text("Got lost? Select 'Help' in menu, or just press F1 key.\n\n"
            "Не знаете с чего начать? Выберите 'Help' в меню, чтобы вызвать краткую справку на русском языке. Или просто нажмите клавишу F1.")

    def print(self, event=None):
        """Calculate and print some evaluated data."""
        self.TxtView.set_text("{}\n--- Drugs --------------------------------------\n{}".format(str(self.human_model), self.human_model.medication()))


class CalcElectrolytes(Frame):
    def __init__(self, parent, human_model):
        super(CalcElectrolytes, self).__init__(parent)
        self.__form_ready = False
        self.parent = parent
        self.human_model = human_model
        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)

        # ABG INPUT
        fr_abg_entry = LabelFrame(fr_entry, text="ABG basic")
        CreateToolTip(fr_abg_entry, "Compare respiratory and metabolic impact on blood pH")
        fr_abg_entry.pack(side=LEFT, anchor=N)

        Label(fr_abg_entry, text="pH").grid(row=1, column=0)
        self.ctl_sbx_pH = Spinbox(fr_abg_entry, width=4, from_=0, to=14,
            format='%.2f', increment=0.01, command=self.set_model_pH)
        self.ctl_sbx_pH.bind("<Return>", self.set_model_pH)
        self.ctl_sbx_pH.grid(row=1, column=1)

        ctl_btn_abg = Button(fr_abg_entry, text="Reset", command=self.set_input_abg_defaults)
        ctl_btn_abg.grid(row=1, column=2)

        Label(fr_abg_entry, text="pCO2, mmHg").grid(row=2, column=0)
        self.ctl_sbx_pCO2 = Spinbox(fr_abg_entry, width=4, from_=0.0, to=150.0,
            format='%.1f', increment=0.1, command=self.set_model_pCO2)
        self.ctl_sbx_pCO2.bind("<Return>", self.set_model_pCO2)
        self.ctl_sbx_pCO2.grid(row=2, column=1)  # Default pCO2 40.0 mmHg

        # ELECTROLYTE INPUT
        fr_elec_entry = LabelFrame(fr_entry, text="Electrolytes")
        CreateToolTip(fr_elec_entry, "Find electrolyte imbalance and unmeasurable anion disturbances")
        fr_elec_entry.pack(side=LEFT, anchor=N)

        Label(fr_elec_entry, text='K, mmol/L').grid(row=1, column=0)
        self.ctl_sbx_K = Spinbox(fr_elec_entry, width=3, from_=0, to=15,
            format='%2.1f', increment=0.1, command=self.set_model_K)
        self.ctl_sbx_K.bind("<Return>", self.set_model_K)
        self.ctl_sbx_K.grid(row=1, column=1)

        Label(fr_elec_entry, text='Na, mmol/L').grid(row=2, column=0)
        self.ctl_sbx_Na = Spinbox(fr_elec_entry, width=3, from_=0.0, to=200.0,
            format='%3.0f', increment=1, command=self.set_model_Na)
        self.ctl_sbx_Na.bind("<Return>", self.set_model_Na)
        self.ctl_sbx_Na.grid(row=2, column=1)

        Label(fr_elec_entry, text='Cl, mmol/L').grid(row=3, column=0)
        self.ctl_sbx_Cl = Spinbox(fr_elec_entry, width=3, from_=0.0, to=200.0,
            format='%3.0f', increment=1, command=self.set_model_Cl)
        self.ctl_sbx_Cl.bind("<Return>", self.set_model_Cl)
        self.ctl_sbx_Cl.grid(row=3, column=1)

        ctl_btn_elec = Button(fr_elec_entry, text="Reset",
            command=self.set_input_elec_defaults)
        ctl_btn_elec.grid(row=1, column=2)

        self.TxtView = TextView2(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.set_input_abg_defaults()
        self.set_input_elec_defaults()
        self.TxtView.set_text(textwrap.dedent("""\
            Make sure you set sex, body weight.

            Use real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap.

            Same applies for analytical errors in lab: garbage in - grabage out. Some imagined book case studies will fail too.
            """))
        # This one is good: https://web.archive.org/web/20170829095349/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Cases.html

    def set_input_abg_defaults(self, event=None):
        self.ctl_sbx_pH.delete(0, END)
        self.ctl_sbx_pH.insert(0, '7.40')  # cm
        self.set_model_pH()
        self.ctl_sbx_pCO2.delete(0, END)
        self.ctl_sbx_pCO2.insert(0, 40.0)  # kg
        self.set_model_pCO2()

    def set_input_elec_defaults(self, event=None):
        self.ctl_sbx_K.delete(0, END)
        self.ctl_sbx_K.insert(0, 4.3)
        self.set_model_K()
        self.ctl_sbx_Na.delete(0, END)
        self.ctl_sbx_Na.insert(0, 140)
        self.set_model_Na()
        self.ctl_sbx_Cl.delete(0, END)
        self.ctl_sbx_Cl.insert(0, 105)
        self.set_model_Cl()

    def set_model_pH(self, event=None):
        self.human_model.blood.pH = float(self.ctl_sbx_pH.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_pCO2(self, event=None):
        self.human_model.blood.pCO2 = float(self.ctl_sbx_pCO2.get()) * abg.kPa
        self.event_generate("<<HumanModelChanged>>")

    def set_model_K(self, event=None):
        self.human_model.blood.K = float(self.ctl_sbx_K.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_Na(self, event=None):
        self.human_model.blood.Na = float(self.ctl_sbx_Na.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_Cl(self, event=None):
        self.human_model.blood.Cl = float(self.ctl_sbx_Cl.get())
        self.event_generate("<<HumanModelChanged>>")

    def print(self, event=None):
        info = "{}\n".format(self.human_model.blood.describe_pH())
        info += "{}\n".format(self.human_model.blood.describe_experimental())
        self.TxtView.set_text(info)


class CalcGFR(Frame):
    """Esimate glomerular filtration rate (eGFR)"""
    def __init__(self, parent, human_model):
        super(CalcGFR, self).__init__(parent)
        self.parent = parent
        self.human_model = human_model

        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)

        Label(fr_entry, text="cCrea, μmol/L").pack(side=LEFT)
        self.ctl_sbx_ccrea = Spinbox(fr_entry, width=4, from_=0.0, to=1000.0,
            format='%.1f', increment=1, command=self.print)
        self.ctl_sbx_ccrea.bind("<Return>", self.print)
        self.ctl_sbx_ccrea.pack(side=LEFT)
        CreateToolTip(self.ctl_sbx_ccrea, "Serum creatinine (IDMS-calibrated)")

        Label(fr_entry, text="Age, years").pack(side=LEFT)
        self.ctl_sbx_age = Spinbox(fr_entry, width=3, from_=0.0, to=200.0,
            format='%1.0f', increment=1, command=self.set_model_age)
        self.ctl_sbx_age.bind("<Return>", self.set_model_age)
        self.ctl_sbx_age.pack(side=LEFT)
        CreateToolTip(self.ctl_sbx_age, "Human age, years")

        self.var_isblack = IntVar()  # No real body weight
        self.var_isblack.set(0)
        self.ctl_ckb_isblack = Checkbutton(fr_entry, variable=self.var_isblack, onvalue=1, offvalue=0, text="Black human", command=self.print)
        self.ctl_ckb_isblack.pack(side=LEFT)
        CreateToolTip(self.ctl_ckb_isblack, "Is this human skin is black?")

        self.reset = Button(fr_entry, text="Reset", command=self.set_input_defaults)
        self.reset.pack(side=LEFT)
        CreateToolTip(self.reset, "Drop changes for cCrea, age, skin")

        self.TxtView = TextView2(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.set_input_defaults()
        self.TxtView.set_text("Estimate glomerular filtration rate (eGFR).\n"
            "Make sure you set sex, cCrea (IDMS-calibrated), age, skin color.")

    def set_input_defaults(self, event=None):
        self.ctl_sbx_ccrea.delete(0, END)
        self.ctl_sbx_ccrea.insert(0, 75.0)

        self.ctl_sbx_age.delete(0, END)
        self.ctl_sbx_age.insert(0, 40)
        self.set_model_age()

        self.var_isblack.set(0)
        self.print()

    def set_model_age(self, event=None):
        self.human_model.age = float(self.ctl_sbx_age.get())
        self.event_generate("<<HumanModelChanged>>")

    def print(self, event=None):
        sex = self.human_model.sex
        if sex in ('male', 'female'):
            cCrea = float(self.ctl_sbx_ccrea.get())
            age = self.human_model.age
            black_skin = (self.var_isblack.get() == 1)
            mdrd = abg.egfr_mdrd(sex, cCrea, age, black_skin)
            epi = abg.egfr_ckd_epi(sex, cCrea, age, black_skin)
            info = """\
            cCrea {:.2f} mg/dl
            MDRD\t{:3.0f} mL/min/1.73 m2 (considered obsolete)
            CKD-EPI\t{:3.0f} mL/min/1.73 m2

            {}
            """.format(cCrea / 88.4, mdrd, epi, abg.gfr_describe(epi))
        else:
            info = "Don't know how to calculate eGFR in paed"
        self.TxtView.set_text(textwrap.dedent(info))


class CreateToolTip(object):
    """Create a tooltip for a given widget."""
    def __init__(self, widget, text="Widget's empty tooltip"):
        self.waittime = 500     # miliseconds
        self.wraplength = 180   # pixels
        self.widget = widget
        self.text = text
        self.widget.bind("<Enter>", self.enter)
        self.widget.bind("<Leave>", self.leave)
        self.widget.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.widget.after(self.waittime, self.showtip)

    def unschedule(self):
        _id = self.id
        self.id = None
        if _id:
            self.widget.after_cancel(_id)

    def showtip(self, event=None):
        x = y = 0
        x, y, cx, cy = self.widget.bbox(INSERT)
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        # Creates a toplevel window
        self.tw = Toplevel(self.widget)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry("+%d+%d" % (x, y))
        label = Label(self.tw, text=self.text, justify=LEFT,
            background="#ffffff", relief='solid', borderwidth=1,
            wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw, self.tw = self.tw, None
        if tw:
            tw.destroy()


def main():
    root = Tk()
    MainWindow(root).pack(expand=True, fill=BOTH)
    root.mainloop()


if __name__ == '__main__':
    main()
