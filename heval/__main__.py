#!/usr/bin/env python
# -*- coding: utf-8 -*-

import random
import textwrap
from datetime import datetime
from tkinter import *
from tkinter import scrolledtext
from tkinter import font
from tkinter.ttk import *
from heval import abg
from heval import human
from heval import __version__


__helptext__ = """\
  HUMAN BODY
Введите пол и рост — этого достаточно для большей части антропометрических \
расчётов. Идеальный вес (IBW) рассчитывается по росту и полу автоматически. \
Снимите галочку "Use IBW" и введите реальный вес, если знаете его.

Мгновенно доступны: IBW, BSA, BMI, объёмы вентиляции, суточная потребность \
в энергии и жидкости, диурез, дозировки ЛС etc.

  ABG & ELECTROLYTES
Кислотно-щелочной статус оценивается по pH и pCO2. Но в случае \
метаболического ацидоза необходимо ввести концентрации K⁺, Na⁺, Cl⁻, чтобы \
программа смогла рассчитать анионный промежуток и попыталась найти скрытые \
метаболические процессы при помощи Delta ratio.
Пол и вес влияют на рассчитанную инфузионную терапию.

При наведении курсора на поле ввода появляется всплывающая подсказка.

  ABBREVIATIONS
ABG - arterial blood gas test
AG - anion gap
AKI - acute kidney injury
BMI - body mass index
BMR - basal metabolic rate
BSA - body surface area, m²
CKD - chronic kidney disease
D5 - dextrose 5%
DKE - diabetic ketoacidosis
eGFR - estimated glomerular filtration rate
GA - general anesthesia
gg - gap-gap, delta gap
HAGMA - high anion gap metabolic acidosis
HHS - hyperosmolar hyperglycemic state
IBW - ideal body weight, kg
IV, I/V - intravenous
KULT - Ketones, Uremia, Lactate, Toxins
MV - minute volume
NAGMA - normal anion gap metabolic acidosis
NMT - neuromuscular monitoring
pRBC - packed red blood cells
RBW - real body weight, kg
RR - respiratory rate
SBE - standard base excess
TIVA - total intravenous anesthesia
TOF - train of four
TV - tidal volume
UUN - Urine Urea Nitrogen
VDaw - dead space airway volume

ПосДеж - Пособие дежуранта, С.А. Деревщиков, 2014 г
"""

__about__ = """\
Heval — экспериментальное программное обеспечение, предназначенное для \
использования врачами-анестезиологами-реаниматологами. Программа \
предоставляется "как есть". Автор не несёт ответственности за ваши \
действия и не предоставляет никаких гарантий.

Heval is an experimental medical software intended for healthcare \
specialists. Software is provided ​"as is". Developer makes no warranties, \
express or implied.

Written by Eugene Dvoretsky 2015-2020. Check source code for references and \
formulas. Contact E-mail: radioxoma@gmail.com

Heval is a free software and licensed under the terms of \
GNU General Public License version 3."""


__easter_text__ = ("It's got what plants crave!", "It's got electrolytes!")


class MainWindow(Frame):
    def __init__(self, parent=None, *args, **kwargs):
        super(MainWindow, self).__init__(parent, *args, **kwargs)
        self.parent = parent
        self.parent.title("Heval — a human evaluator v{}".format(__version__))
        self.parent.geometry("600x590")

        self.parent.style = Style()
        self.parent.style.theme_use('clam')  # ('clam', 'alt', 'default', 'classic')
        self.parent.style.configure('TButton', padding=2)

        self.HBody = human.HumanBodyModel()

        menubar = Menu(self.parent)
        menu_file = Menu(menubar, tearoff=False)
        menu_file.add_command(label="Exit", command=self.parent.destroy, accelerator="Esc")
        menubar.add_cascade(label="File", menu=menu_file)

        menu_view = Menu(menubar, tearoff=False)
        self._debug = BooleanVar()
        self._debug.set(self.HBody.debug)  # Model debug flag is superior
        menu_view.add_checkbutton(label="Verbose report", command=self.set_model_debug, variable=self._debug, accelerator="v")
        menu_view.add_command(label="Increase font size", command=lambda: self.adjust_font_size('increase'), accelerator="Ctrl++")
        menu_view.add_command(label="Decrease font size", command=lambda: self.adjust_font_size('decrease'), accelerator="Ctrl+-")
        menu_view.add_command(label="Default font size", command=lambda: self.adjust_font_size(), accelerator="Ctrl+0")
        menubar.add_cascade(label="View", menu=menu_view)

        menu_about = Menu(menubar, tearoff=False)
        menu_about.add_command(label="Help", command=lambda: HelpWindow(self.parent), accelerator="F1")
        menu_about.add_command(label="Website and updates", command=visit_website)
        menu_about.add_command(label="About...", command=lambda: AboutWindow(self.parent))
        menubar.add_cascade(label="Help", menu=menu_about)
        self.parent['menu'] = menubar


        nb = Notebook(self)
        self.create_input()
        self.set_input_defaults()
        self.adjust_font_size()
        self.MText = MainText(nb, self.HBody)
        self.CNutrition = CalcNutrition(nb, self.HBody)
        self.CElectrolytes = CalcElectrolytes(nb, self.HBody)
        self.CGFR = CalcGFR(nb, self.HBody)
        nb.add(self.MText, text="Human body")
        nb.add(self.CNutrition, text="Nutrition")
        nb.add(self.CElectrolytes, text="ABG & Electrolytes")
        nb.add(self.CGFR, text='eGFR')
        nb.pack(expand=True, fill=BOTH)  # BOTH looks less ugly under Windows

        self.parent.bind('<Escape>', lambda e: self.parent.destroy())
        self.bind_all('<F1>', lambda e: HelpWindow(self.parent))
        self.bind_all('<v>', self.set_model_debug)
        self.bind_all('<Control-Key-equal>', lambda e: self.adjust_font_size('increase'))
        self.bind_all('<Control-Key-minus>', lambda e: self.adjust_font_size('decrease'))
        self.bind_all('<Control-Key-0>', lambda e: self.adjust_font_size())
        # self.bind('<r>', lambda e: self.set_input_defaults())
        # self.bind('<Control-s>', lambda e: self.save_text())
        # self.bind('<Control-a>', lambda e: self.select_all())
        # self.bind('<Control-c>', lambda e: self.copy_text())
        self.parent.bind('<Alt-KeyPress-1>', lambda e: nb.select(0))
        self.parent.bind('<Alt-KeyPress-2>', lambda e: nb.select(1))
        self.parent.bind('<Alt-KeyPress-3>', lambda e: nb.select(2))
        self.parent.bind('<Alt-KeyPress-4>', lambda e: nb.select(3))
        self.bind_all('<<HumanModelChanged>>', self.eval)
        self.bind_all('<<HumanModelChanged>>', self.MText.eval, add='+')
        self.bind_all('<<HumanModelChanged>>', self.CNutrition.eval, add='+')
        self.bind_all('<<HumanModelChanged>>', self.CElectrolytes.eval, add='+')
        self.bind_all('<<HumanModelChanged>>', self.CGFR.eval, add='+')

        # self.statusbar_str = StringVar()
        # self.statusbar_str.set("Hello world!")
        # statusbar = Label(self, textvariable=self.statusbar_str, relief=SUNKEN, anchor=W)
        # statusbar.pack(side=BOTTOM, fill=X)

    def adjust_font_size(self, event=None):
        """Set default font size or adjust current size.

        Bug 1. Detect actual monospaced font name and hardcode size to 9
        on Windows it's Courier new 10pt, on Linux DejaVu Sans Mono 9 pt

        Bug 2. Must be called once on __init__ without parameters, because
        `some_font['size']` has negative value by default.
        """
        for fontvar in ('TkDefaultFont', 'TkTextFont', 'TkFixedFont', 'TkMenuFont'):
            font_obj = font.nametofont(fontvar)
            # print(font_obj.actual())
            # font_obj = font.Font(font=fontvar)
            if event == 'increase':
                font_obj['size'] += 1
            elif event == 'decrease':
                font_obj['size'] -= 1
            else:  # Set default font size
                font_obj['size'] = 9

    def create_input(self):
        """One row of input widgets."""
        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)
        Label(fr_entry, text='Sex').pack(side=LEFT)
        self.ctl_sex = Combobox(fr_entry, values=['Male', 'Female', 'Child'], width=7)
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
        self.ctl_use_ibw_cb = Checkbutton(
            fr_entry, variable=self.var_use_ibw, onvalue=1, offvalue=0,
            text="Use IBW", command=self.set_model_use_ibw)
        self.ctl_use_ibw_cb.pack(side=LEFT)
        CreateToolTip(self.ctl_use_ibw_cb, "Estimate ideal body weight from height\nand use IBW instead RBW in all calculations")

        self.lbl_weight = Label(fr_entry, text='Weight, kg')
        self.lbl_weight.pack(side=LEFT)
        self.ctl_weight = Spinbox(
            fr_entry, width=4, from_=1, to=500,
            format='%.1f', increment=1, command=self.set_model_weight)
        self.ctl_weight.bind("<Return>", self.set_model_weight)
        self.ctl_weight.pack(side=LEFT)
        CreateToolTip(self.ctl_weight, "Real body weight")

        Label(fr_entry, text='Body temp, °C').pack(side=LEFT)
        self.ctl_sbx_temp = Spinbox(
            fr_entry, width=4, from_=0.0, to=50.0,
            format='%.1f', increment=0.1, command=self.set_model_body_temp)
        self.ctl_sbx_temp.bind("<Return>", self.set_model_body_temp)
        self.ctl_sbx_temp.pack(side=LEFT)
        CreateToolTip(self.ctl_sbx_temp, "Axillary temperature, used for perspiration evaluation")

        reset = Button(fr_entry, text="Reset", command=self.set_input_defaults)
        reset.pack(side=LEFT)
        CreateToolTip(reset, "Set default values for sex, height, real body weight, temp")

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

    def set_model_debug(self, event=None):
        """Be verbose if debug is True.
        """
        self.HBody.debug = not self.HBody.debug  # Invert boolean
        self._debug.set(self.HBody.debug)  # Change flag in menu accordingly
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        """Update GUI."""
        if self.HBody.use_ibw:
            self.ctl_weight['state'] = NORMAL
            self.ctl_weight.delete(0, END)
            self.ctl_weight.insert(0, round(self.HBody.weight, 1))
            self.ctl_weight['state'] = self.lbl_weight['state']


class HelpWindow(Toplevel):
    def __init__(self, parent=None):
        super(HelpWindow, self).__init__(parent)
        self.parent = parent
        x = self.parent.winfo_x()
        y = self.parent.winfo_y()
        self.geometry("+{:.0f}+{:.0f}".format(x + 50, y + 100))
        self.title('Help')

        self.text = scrolledtext.ScrolledText(self, wrap=WORD)
        self.text.insert(1.0, __helptext__)

        # Mimic Label colors
        lbl_bg = Style().lookup('TLabel', 'background')
        lbl_font = Style().lookup('TLabel', 'font')  # TkDefaultFont
        self.configure(bg=lbl_bg)
        # relief=FLAT for Linux
        self.text.configure(relief=FLAT, state=DISABLED, bg=lbl_bg, font=lbl_font)
        self.text.pack(expand=True, fill=BOTH)

        self.ctl_frame = Frame(self, padding=8)
        self.ctl_btn_close = Button(self.ctl_frame, text="Close", command=self.destroy)
        self.ctl_btn_close.pack(side=RIGHT)
        self.ctl_frame.pack(fill=BOTH)
        self.bind('<Escape>', lambda e: self.destroy())
        self.focus_set()

        self.popup_menu = Menu(self, tearoff=False)
        self.popup_menu.add_command(label="Copy", command=self.copy, accelerator="Ctrl+C")
        self.popup_menu.add_command(label="Copy all", command=self.copy_all)
        self.bind("<ButtonRelease-3>", self.popup)
        self.bind('<Control-C>', self.copy)

    def popup(self, event):
        self.popup_menu.tk_popup(event.x_root, event.y_root)

    def copy(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.text.get("sel.first", "sel.last"))
        self.update()  # Force copy

    def copy_all(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.text.get(1.0, END))


class AboutWindow(Toplevel):
    def __init__(self, parent=None):
        super(AboutWindow, self).__init__(parent)
        self.parent = parent
        x = self.parent.winfo_x()
        y = self.parent.winfo_y()
        self.geometry("+{:.0f}+{:.0f}".format(x + 50, y + 100))
        self.title('About v{}'.format(__version__))

        abouttext = __about__ + " And remember: {}".format(
            random.choice(__easter_text__))
        self.lbl = Label(self, text=abouttext, wraplength=500, padding=8)
        self.lbl.pack(expand=True, fill=BOTH)

        self.ctl_frame = Frame(self, padding=8)
        self.ctl_btn_website = Button(self.ctl_frame, text="Visit website", command=visit_website)
        CreateToolTip(self.ctl_btn_website, "Source code, docs and updates")
        self.ctl_btn_close = Button(self.ctl_frame, text="Close", command=self.destroy)
        self.ctl_btn_close.pack(side=RIGHT)
        self.ctl_btn_website.pack(side=RIGHT)
        self.ctl_frame.pack(fill=BOTH)
        self.bind('<Escape>', lambda e: self.destroy())
        self.focus_set()


class TextViewCustom(Frame):
    def __init__(self, *args, **kwargs):
        super(TextViewCustom, self).__init__(parent, *args, **kwargs)
        self.parent = parent

        frm_txt = Frame(self, width=450, height=300)
        frm_txt.pack(expand=True, fill=BOTH)
        frm_txt.grid_propagate(False)  # ensure a consistent GUI size
        frm_txt.grid_rowconfigure(0, weight=1)
        frm_txt.grid_columnconfigure(0, weight=1)  # implement stretchability

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


class TextView(scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        super(TextView, self).__init__(*args, **kwargs)
        self.config(font='TkFixedFont', wrap='word')
        self.popup_menu = Menu(self, tearoff=False)
        self.popup_menu.add_command(label="Copy", command=self.copy, accelerator="Ctrl+C")
        self.popup_menu.add_command(label="Copy all", command=self.copy_all)
        self.bind("<ButtonRelease-3>", self.popup)
        self.bind('<Control-C>', self.copy)

    def popup(self, event):
        self.popup_menu.tk_popup(event.x_root, event.y_root)

    def copy(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.get("sel.first", "sel.last"))
        self.update()  # Force copy

    def copy_all(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.get(1.0, END))

    def set_text(self, text):
        """Replace current text."""
        self['state'] = NORMAL
        self.delete(1.0, END)
        self.insert(END, text)
        self['state'] = DISABLED


class MainText(Frame):
    def __init__(self, parent, human_model):
        super(MainText, self).__init__(parent)
        self.parent = parent
        self.human_model = human_model

        self.TxtView = TextView(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.TxtView.set_text(textwrap.dedent("""\
        Just set sex and height. Open \"Help\" from menu or by pressing F1 key.

        Не знаете с чего начать? Выберите \"Help\" в меню, чтобы вызвать краткую справку на русском языке. Или просто нажмите клавишу F1.
        """))

    def eval(self, event=None):
        """Calculate and print some evaluated data."""
        info = "{}\n".format(self.human_model.describe_body())
        info += "{}\n".format(self.human_model.describe_drugs())
        self.TxtView.set_text(info)


class CalcNutrition(Frame):
    def __init__(self, parent, human_model):
        super(CalcNutrition, self).__init__(parent)
        self.parent = parent
        self.human_model = human_model

        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)

        self.var_rbtm_calc_method = IntVar()
        self.var_rbtm_calc_method.set(0)

        # Fluid input
        fr_fluid_entry = LabelFrame(fr_entry, text="Daily fluid")
        fr_fluid_entry.pack(side=LEFT, anchor=N, expand=True, fill=BOTH)

        ctl_btn_fluid = Button(fr_fluid_entry, text="Reset", command=self.set_input_fluid_defaults)
        # CreateToolTip(ctl_btn_fluid, "Reset fluid")
        ctl_btn_fluid.grid(row=0, column=0)

        Label(fr_fluid_entry, text="ml/kg/24h").grid(row=1, column=0)
        self.ctl_sbx_fluid_mul = Spinbox(
            fr_fluid_entry, width=3, from_=0.0, to=200.0,
            format='%1.0f', increment=1, command=self.set_model_fluid_multipler)
        self.ctl_sbx_fluid_mul.bind("<Return>", self.set_model_fluid_multipler)
        self.ctl_sbx_fluid_mul.grid(row=1, column=1)
        CreateToolTip(self.ctl_sbx_fluid_mul, "24 hours fluid demand.\nTypical 30-35 ml/kg.")

        Label(fr_fluid_entry, text="ml/24h").grid(row=2, column=0)
        self.lbl_fluid_24h = Label(fr_fluid_entry)
        self.lbl_fluid_24h.grid(row=2, column=1)

        # Kcal input
        self.fr_kcal_entry = LabelFrame(fr_entry, text="By calorie demand")
        self.fr_kcal_entry.pack(side=LEFT, anchor=N, expand=True, fill=BOTH)

        ctl_btn_kcal = Button(self.fr_kcal_entry, text="Reset", command=self.set_input_kcal_defaults)
        # CreateToolTip(ctl_btn_kcal, "Reset kcal")
        ctl_btn_kcal.grid(row=0, column=0)

        ctl_rbtn0_method = Radiobutton(
            self.fr_kcal_entry, text=None, variable=self.var_rbtm_calc_method,
            value=0, command=self.set_nutr_gui_state)
        ctl_rbtn0_method.grid(row=0, column=1)
        CreateToolTip(ctl_rbtn0_method, "Calculate daily nutrition dose by calorie (not protein) requirement")

        Label(self.fr_kcal_entry, text="kcal/kg/24h").grid(row=1, column=0)
        self.ctl_sbx_kcal_mul = Spinbox(
            self.fr_kcal_entry, width=2, from_=0.0, to=99.0,
            format='%1.0f', increment=1, command=self.set_model_kcal_multipler)
        self.ctl_sbx_kcal_mul.bind("<Return>", self.set_model_kcal_multipler)
        self.ctl_sbx_kcal_mul.grid(row=1, column=1)
        CreateToolTip(self.ctl_sbx_kcal_mul, "24 hours energy demand.\nTypical 25-30 kcal/kg.")

        Label(self.fr_kcal_entry, text="kcal/24h").grid(row=2, column=0)
        self.lbl_kcal_24h = Label(self.fr_kcal_entry)
        self.lbl_kcal_24h.grid(row=2, column=1)

        # Protein & Nitrogen balance input
        self.fr_nitrogen_entry = LabelFrame(fr_entry, text="By nitrogen balance")
        self.fr_nitrogen_entry.pack(side=LEFT, anchor=N, expand=True, fill=BOTH)

        ctl_btn_prot = Button(
            self.fr_nitrogen_entry, text="Reset",
            command=self.set_input_protein_defaults)
        # CreateToolTip(ctl_btn_prot, "Reset protein")
        ctl_btn_prot.grid(row=0, column=0)

        ctl_rbtn1_method = Radiobutton(
            self.fr_nitrogen_entry, text=None, variable=self.var_rbtm_calc_method,
            value=1, command=self.set_nutr_gui_state)
        ctl_rbtn1_method.grid(row=0, column=1)
        CreateToolTip(ctl_rbtn1_method, "Calculate daily nutrition dose by measured protein (not calorie) requirement")

        Label(self.fr_nitrogen_entry, text="Urine urea, mmol/24h").grid(row=1, column=0)
        self.ctl_sbx_uurea = Spinbox(
            self.fr_nitrogen_entry, width=4, from_=0.0, to=9999.0,
            format='%.0f', increment=10, command=self.set_model_uurea)
        self.ctl_sbx_uurea.bind("<Return>", self.set_model_uurea)
        self.ctl_sbx_uurea.grid(row=1, column=1)
        CreateToolTip(self.ctl_sbx_uurea, "Urine urea excreted during 24h (equals to total urea nitrogen, when measured in mmol/24h)")

        Label(self.fr_nitrogen_entry, text="Protein g/24h").grid(row=2, column=0)
        self.lbl_prot_24h = Label(self.fr_nitrogen_entry)
        self.lbl_prot_24h.grid(row=2, column=1)
        CreateToolTip(self.lbl_prot_24h, "24h protein intake needed to maintain zero nitrogen balance")

        Label(self.fr_nitrogen_entry, text="Protein, g/kg/24h").grid(row=3, column=0)
        # self.ctl_sbx_prot_g_kg_24h = Spinbox(
        #     self.fr_nitrogen_entry, width=4, from_=0.0, to=10.0,
        #     format='%.2f', increment=0.1, command=self.increment_uurea_widget)
        # self.ctl_sbx_prot_g_kg_24h.bind("<Return>", self.eval)
        # self.ctl_sbx_prot_g_kg_24h.grid(row=2, column=1)
        # CreateToolTip(self.ctl_sbx_prot_g_kg_24h, "Urine urea concentration in 24h sample")
        self.lbl_sbx_prot_g_kg_24h = Label(self.fr_nitrogen_entry)
        self.lbl_sbx_prot_g_kg_24h.grid(row=3, column=1)

        self.TxtView = TextView(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.set_input_fluid_defaults()
        self.set_input_kcal_defaults()
        self.set_input_protein_defaults()
        self.set_nutr_gui_state()
        self.TxtView.set_text(textwrap.dedent("""\
            Just set sex and height.

            Nutrition mixtures dosage can be estimated in two ways:
              * As daily calorie goal by weight (kcal/kg/24h)
              * As daily protein goal by nitrogen balance (urea nitrogen loss mmol/24h) or expected protein demand (g/kg/24h) which are dependent on each other

            Heval will suggest additional fluid if nutrition mixture doesn't contain full 24h volume. Negative value means fluid excess.
            """))

    def set_input_fluid_defaults(self, event=None):
        self.ctl_sbx_fluid_mul.delete(0, END)
        self.ctl_sbx_fluid_mul.insert(0, 30)  # ml/kg/24h
        self.set_model_fluid_multipler()

    def set_input_kcal_defaults(self, event=None):
        self.ctl_sbx_kcal_mul.delete(0, END)
        self.ctl_sbx_kcal_mul.insert(0, 25)  # kcal/kg/24h
        self.set_model_kcal_multipler()

    def set_input_protein_defaults(self, event=None):
        self.ctl_sbx_uurea.delete(0, END)
        self.ctl_sbx_uurea.insert(0, 190)  # Corresponds to 0.8 g/kg/h
        self.set_model_uurea()

    def set_nutr_gui_state(self, event=None):
        def set_state(widget, state):
            # Set all subwidgets state NORMAL, DISABLED
            for child in widget.winfo_children():
                if not isinstance(child, Radiobutton):
                    child.configure(state=state)

        if self.var_rbtm_calc_method.get() == 0:  # By kcal
            set_state(self.fr_kcal_entry, NORMAL)
            set_state(self.fr_nitrogen_entry, DISABLED)
        elif self.var_rbtm_calc_method.get() == 1:  # By UUN
            set_state(self.fr_kcal_entry, DISABLED)
            set_state(self.fr_nitrogen_entry, NORMAL)
        self.eval()

    def set_model_fluid_multipler(self, event=None):
        self.human_model.nutrition.fluid_multipler = float(
            self.ctl_sbx_fluid_mul.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_kcal_multipler(self, event=None):
        self.human_model.nutrition.kcal_multipler = float(
            self.ctl_sbx_kcal_mul.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_uurea(self, event=None):
        self.human_model.nutrition.uurea = float(self.ctl_sbx_uurea.get())
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        """Calculate and print some evaluated data."""
        self.lbl_fluid_24h['text'] = round(self.human_model.nutrition.fluid_24h)
        self.lbl_kcal_24h['text'] = round(self.human_model.nutrition.kcal_24h)
        self.lbl_prot_24h['text'] = "{:.1f}".format(self.human_model.nutrition.uurea_prot_24h)
        self.lbl_sbx_prot_g_kg_24h['text'] = "{:.2f}".format(self.human_model.nutrition.uures_prot_g_kg_24h)
        # self.ctl_sbx_prot_g_kg_24h.delete(0, END)
        # self.ctl_sbx_prot_g_kg_24h.insert(0, round(self.human_model.nutrition.uures_prot_g_kg_24h, 2))  # g/kg/24h
        info = ""
        if self.var_rbtm_calc_method.get() == 0:  # By kcal
            info += "{}\n".format(self.human_model.nutrition.describe_nutrition())
        elif self.var_rbtm_calc_method.get() == 1:  # By UUN
            info += "{}\n".format(self.human_model.nutrition.describe_nutrition(by_protein=True))
        self.TxtView.set_text(info)


class CalcElectrolytes(Frame):
    def __init__(self, parent, human_model):
        super(CalcElectrolytes, self).__init__(parent)
        self.__form_ready = False
        self.parent = parent
        self.human_model = human_model
        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)

        # ABG INPUT
        fr_abg_entry = LabelFrame(fr_entry, text="Basic ABG")
        fr_abg_entry.pack(side=LEFT, anchor=N, expand=True, fill=BOTH)

        ctl_btn_abg = Button(fr_abg_entry, text="Reset", command=self.set_input_abg_defaults)
        CreateToolTip(ctl_btn_abg, "Compare respiratory and metabolic impact on blood pH")
        ctl_btn_abg.grid(row=1, column=0)

        Label(fr_abg_entry, text="pH").grid(row=2, column=0)
        self.ctl_sbx_pH = Spinbox(
            fr_abg_entry, width=4, from_=0, to=14,
            format='%.2f', increment=0.01, command=self.set_model_pH)
        self.ctl_sbx_pH.bind("<Return>", self.set_model_pH)
        self.ctl_sbx_pH.grid(row=2, column=1)

        Label(fr_abg_entry, text="pCO₂, mmHg").grid(row=3, column=0)
        self.ctl_sbx_pCO2 = Spinbox(
            fr_abg_entry, width=4, from_=0.0, to=150.0,
            format='%.1f', increment=1, command=self.set_model_pCO2)
        self.ctl_sbx_pCO2.bind("<Return>", self.set_model_pCO2)
        self.ctl_sbx_pCO2.grid(row=3, column=1)  # Default pCO2 40.0 mmHg

        Label(fr_abg_entry, text="HCO₃(P), mmol/L").grid(row=4, column=0)
        self.lbl_hco3 = Label(fr_abg_entry)
        CreateToolTip(self.lbl_hco3, "Actual bicarbonate")
        self.lbl_hco3.grid(row=4, column=1)

        # ELECTROLYTE INPUT
        fr_elec_entry = LabelFrame(fr_entry, text="Electrolytes")
        fr_elec_entry.pack(side=LEFT, anchor=N, expand=True, fill=BOTH)

        ctl_btn_elec = Button(
            fr_elec_entry, text="Reset",
            command=self.set_input_elec_defaults)
        CreateToolTip(ctl_btn_elec, "Find electrolyte imbalance and unmeasurable anion disturbances")
        ctl_btn_elec.grid(row=1, column=0)

        Label(fr_elec_entry, text='K⁺, mmol/L').grid(row=2, column=0)
        self.ctl_sbx_K = Spinbox(
            fr_elec_entry, width=3, from_=0, to=15,
            format='%2.1f', increment=0.1, command=self.set_model_K)
        self.ctl_sbx_K.bind("<Return>", self.set_model_K)
        self.ctl_sbx_K.grid(row=2, column=1)

        Label(fr_elec_entry, text='Na⁺, mmol/L').grid(row=3, column=0)
        self.ctl_sbx_Na = Spinbox(
            fr_elec_entry, width=3, from_=0.0, to=200.0,
            format='%3.0f', increment=1, command=self.set_model_Na)
        CreateToolTip(self.ctl_sbx_Na, "Na⁺ and cGlu are used for serum osmolarity calculations")
        self.ctl_sbx_Na.bind("<Return>", self.set_model_Na)
        self.ctl_sbx_Na.grid(row=3, column=1)

        Label(fr_elec_entry, text='Cl⁻, mmol/L').grid(row=4, column=0)
        self.ctl_sbx_Cl = Spinbox(
            fr_elec_entry, width=3, from_=0.0, to=200.0,
            format='%3.0f', increment=1, command=self.set_model_Cl)
        self.ctl_sbx_Cl.bind("<Return>", self.set_model_Cl)
        self.ctl_sbx_Cl.grid(row=4, column=1)

        # EXTRA INPUT
        fr_extra_entry = LabelFrame(fr_entry, text="Optional data")
        fr_extra_entry.pack(side=LEFT, anchor=N, expand=True, fill=BOTH)

        ctl_btn_elec = Button(
            fr_extra_entry, text="Reset",
            command=self.set_input_extra_defaults)
        CreateToolTip(ctl_btn_elec, "Tweak electrolyte calculations like a pro")
        ctl_btn_elec.grid(row=1, column=0)

        Label(fr_extra_entry, text="cGlu, mmol/L").grid(row=2, column=0)
        self.ctl_sbx_cGlu = Spinbox(
            fr_extra_entry, width=4, from_=0, to=50,
            format='%.1f', increment=0.1, command=self.set_model_cGlu)
        CreateToolTip(self.ctl_sbx_cGlu, "Enter glucose to properly calculate serum osmolarity (formula is '2Na⁺ + cGlu').\n\nIf patient blood contains other osmotically active molecules, such as ethanol or BUN (due to kidney damage), you shall add it manually or use lab osmometer.")
        self.ctl_sbx_cGlu.bind("<Return>", self.set_model_cGlu)
        self.ctl_sbx_cGlu.grid(row=2, column=1)

        Label(fr_extra_entry, text="ctAlb, g/dL").grid(row=3, column=0)
        self.ctl_sbx_ctAlb = Spinbox(
            fr_extra_entry, width=4, from_=0, to=15,
            format='%.1f', increment=0.1, command=self.set_model_ctAlb)
        CreateToolTip(self.ctl_sbx_ctAlb, "Enter if anion gap is surprisingly low. Hypoalbuminemia causes low AG in starved humans.")
        self.ctl_sbx_ctAlb.bind("<Return>", self.set_model_ctAlb)
        self.ctl_sbx_ctAlb.grid(row=3, column=1)

        self.TxtView = TextView(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.set_input_abg_defaults()
        self.set_input_elec_defaults()
        self.set_input_extra_defaults()
        self.TxtView.set_text(textwrap.dedent("""\
            Make sure you set sex, body weight.

            Use real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap.

            Same applies for analytical errors in lab: garbage in - grabage out. Some imagined book case studies will fail too.
            """))
        # This one is quite good: https://web.archive.org/web/20170829095349/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Cases.html

    def set_input_abg_defaults(self, event=None):
        self.ctl_sbx_pH.delete(0, END)
        self.ctl_sbx_pH.insert(0, abg.norm_pH_mean)
        self.set_model_pH()
        self.ctl_sbx_pCO2.delete(0, END)
        self.ctl_sbx_pCO2.insert(0, abg.norm_pCO2mmHg_mean)  # kg
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

    def set_input_extra_defaults(self, event=None):
        self.ctl_sbx_cGlu.delete(0, END)
        self.ctl_sbx_cGlu.insert(0, abg.norm_cGlu_mean)
        self.set_model_cGlu()
        self.ctl_sbx_ctAlb.delete(0, END)
        self.ctl_sbx_ctAlb.insert(0, abg.norm_ctAlb_mean)
        self.set_model_ctAlb()

    def set_model_pH(self, event=None):
        self.human_model.blood.pH = float(self.ctl_sbx_pH.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_pCO2(self, event=None):
        self.human_model.blood.pCO2 = float(self.ctl_sbx_pCO2.get()) * abg.kPa
        self.event_generate("<<HumanModelChanged>>")

    def set_model_K(self, event=None):
        self.human_model.blood.cK = float(self.ctl_sbx_K.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_Na(self, event=None):
        self.human_model.blood.cNa = float(self.ctl_sbx_Na.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_Cl(self, event=None):
        self.human_model.blood.cCl = float(self.ctl_sbx_Cl.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_ctAlb(self, event=None):
        self.human_model.blood.ctAlb = float(self.ctl_sbx_ctAlb.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_cGlu(self, event=None):
        self.human_model.blood.cGlu = float(self.ctl_sbx_cGlu.get())
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        self.lbl_hco3['text'] = round(self.human_model.blood.hco3p, 1)
        info = ""
        info += "Basic ABG assessment\n"
        info += "====================\n"
        info += "{}\n".format(self.human_model.blood.describe_abg())
        info += "{}\n\n\n".format(self.human_model.blood.describe_sbe())
        info += "Complex electrolyte assessment\n"
        info += "==============================\n"
        info += "{}\n\n".format(self.human_model.blood.describe_anion_gap())
        info += "{}\n".format(self.human_model.blood.describe_electrolytes())
        info += "{}\n\n".format(self.human_model.blood.describe_glucose())
        info += "{}\n".format(self.human_model.blood.describe_albumin())
        self.TxtView.set_text(info)


class CalcGFR(Frame):
    """Esimate glomerular filtration rate (eGFR)."""
    def __init__(self, parent, human_model):
        super(CalcGFR, self).__init__(parent)
        self.parent = parent
        self.human_model = human_model

        fr_entry = Frame(self)
        fr_entry.pack(anchor=W)

        Label(fr_entry, text="cCrea, μmol/L").pack(side=LEFT)
        self.ctl_sbx_ccrea = Spinbox(
            fr_entry, width=4, from_=0.0, to=1000.0,
            format='%.1f', increment=10, command=self.eval)
        self.ctl_sbx_ccrea.bind("<Return>", self.eval)
        self.ctl_sbx_ccrea.pack(side=LEFT)
        CreateToolTip(self.ctl_sbx_ccrea, "Serum creatinine (IDMS-calibrated)")

        Label(fr_entry, text="Age, years").pack(side=LEFT)
        self.ctl_sbx_age = Spinbox(
            fr_entry, width=3, from_=0.0, to=200.0,
            format='%1.0f', increment=1, command=self.set_model_age)
        self.ctl_sbx_age.bind("<Return>", self.set_model_age)
        self.ctl_sbx_age.pack(side=LEFT)
        CreateToolTip(self.ctl_sbx_age, "Human age, years")

        self.var_isblack = IntVar()  # No real body weight
        self.var_isblack.set(0)
        self.ctl_ckb_isblack = Checkbutton(
            fr_entry, variable=self.var_isblack,
            onvalue=1, offvalue=0, text="Black human", command=self.eval)
        self.ctl_ckb_isblack.pack(side=LEFT)
        CreateToolTip(self.ctl_ckb_isblack, "Is this human skin is black?")

        self.reset = Button(fr_entry, text="Reset", command=self.set_input_defaults)
        self.reset.pack(side=LEFT)
        CreateToolTip(self.reset, "Drop changes for cCrea, age, skin")

        self.TxtView = TextView(self)
        self.TxtView.pack(expand=True, fill=BOTH)
        self.set_input_defaults()
        self.TxtView.set_text(
            "Estimate glomerular filtration rate (eGFR).\n"
            "Make sure you set sex, cCrea (IDMS-calibrated), age, skin color.")

    def set_input_defaults(self, event=None):
        self.ctl_sbx_ccrea.delete(0, END)
        self.ctl_sbx_ccrea.insert(0, 75.0)

        self.ctl_sbx_age.delete(0, END)
        self.ctl_sbx_age.insert(0, 40)
        self.set_model_age()

        self.var_isblack.set(0)
        self.eval()

    def set_model_age(self, event=None):
        self.human_model.age = float(self.ctl_sbx_age.get())
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        sex = self.human_model.sex
        cCrea = float(self.ctl_sbx_ccrea.get())
        cCrea_mgdl = cCrea / abg.m_Crea
        if sex in ('male', 'female'):
            age = self.human_model.age
            dob = datetime.now().year - age  # timedelta is complicated
            black_skin = (self.var_isblack.get() == 1)
            mdrd = abg.egfr_mdrd(sex, cCrea, age, black_skin)
            epi = abg.egfr_ckd_epi(sex, cCrea, age, black_skin)
            info = """\
            cCrea\t{:.2f} mg/dL
            Year of birth: {:.0f}
            MDRD\t{:3.0f} mL/min/1.73 m2 (considered obsolete)
            CKD-EPI\t{:3.0f} mL/min/1.73 m2

            Conclusion: {}
            """.format(cCrea_mgdl, dob, mdrd, epi, abg.gfr_describe(epi))
        elif sex == 'child':
            schwartz = abg.egfr_schwartz(cCrea, self.human_model.height)
            info = """\
            cCrea\t{:.2f} mg/dL
            {:.0f} mL/min/1.73 m2 [Schwartz revised 2009]
            {}
            """.format(cCrea_mgdl, schwartz, abg.gfr_describe(schwartz))
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
        label = Label(
            self.tw, text=self.text, justify=LEFT,
            background="#ffffff", relief='solid', borderwidth=1,
            wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw, self.tw = self.tw, None
        if tw:
            tw.destroy()


def visit_website(event=None):
    import webbrowser
    webbrowser.open_new_tab("https://github.com/radioxoma/heval")


def main():
    root = Tk()
    MainWindow(root).pack(expand=True, fill=BOTH)
    root.mainloop()


if __name__ == '__main__':
    main()
