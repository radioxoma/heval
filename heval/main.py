#!/usr/bin/env python
# -*- coding: utf-8 -*-

__description__ = """\
Please don't expect much from humans, nor this calculator.

Written by Eugene Dvoretsky 2016-2019.
Check source code for references and formulas.

Программа медицинская, поэтому состоит из допущений чуть менее чем полностью. \
Не используйте лекарственное средство, если не читали его инструкцию.
"""

import textwrap
from tkinter import *
from tkinter import messagebox
from tkinter import scrolledtext
from tkinter import filedialog
from tkinter.ttk import *
import human
import abg


class MainWindow(Tk):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.style = Style()
        self.style.theme_use('clam')  # ('clam', 'alt', 'default', 'classic')
        self.bind('<Escape>', lambda e: self.destroy())
        self.bind_all('<F1>', lambda e: messagebox.showinfo('Help', human.__abbr__))
        # self.bind('<r>', lambda e: self.set_defaults())
        # self.bind('<Control-s>', lambda e: self.save_text())
        # self.bind('<Control-a>', lambda e: self.select_all())
        # self.bind('<Control-c>', lambda e: self.copy_text())
        self.title("Heval — a human evaluator")
        self.geometry("600x420")

        menubar = Menu(self)
        menu_file = Menu(menubar, tearoff=0)
        # menu_file.add_command(label="Reset values", command=self.set_defaults, accelerator="R")
        # menu_file.add_command(label="Save text...", command=self.save_text, accelerator="Ctrl+S")
        menu_file.add_command(label="Exit", command=self.destroy, accelerator="Esc")
        menubar.add_cascade(label="File", menu=menu_file)
        menu_about = Menu(menubar, tearoff=0)
        menu_about.add_command(label="Help", 
            command=lambda: messagebox.showinfo('Help', human.__abbr__), accelerator="F1")
        menu_about.add_command(label="About...",
            command=lambda: messagebox.showinfo('About', __description__))
        menubar.add_cascade(label="Help", menu=menu_about)
        self['menu'] = menubar

        nb = Notebook(self)
        self.TxtView = TextView(nb)
        self.AInterpreter = ABGInterpreter(nb)
        self.CElectrolytes = CalcElectrolytes(nb)
        self.HModel = human.HumanModel()
        self.create_input()

        nb.add(self.TxtView, text='Human')
        nb.add(self.AInterpreter, text='ABG')
        # nb.add(self.CElectrolytes, text='Electrolytes')

        self.bind('<Alt-KeyPress-1>', lambda e: nb.select(0))
        self.bind('<Alt-KeyPress-2>', lambda e: nb.select(1))
        # self.bind('<Alt-KeyPress-3>', lambda e: nb.select(2))

        nb.pack(expand=True, fill=BOTH)

        # self.statusbar_str = StringVar()
        # self.statusbar_str.set("Hello world!")
        # statusbar = Label(self, textvariable=self.statusbar_str, relief=SUNKEN, anchor=W)
        # statusbar.pack(side=BOTTOM, fill=X)
        self.set_input_defaults()

    def create_input(self):
        """One row of widgets."""
        frm_entry = Frame(self)
        frm_entry.pack(fill=BOTH)
        Label(frm_entry, text='Sex').pack(side='left')
        self.ctl_sex = Combobox(frm_entry, values=['Male', 'Female', 'Paed'], width=7)
        self.ctl_sex.bind("<<ComboboxSelected>>", self.set_model_sex)
        self.ctl_sex.pack(side='left')
        CreateToolTip(self.ctl_sex, "Age and sex selector. Calculations quite differ for adults and infants")

        Label(frm_entry, text='Height, cm').pack(side='left')
        self.ctl_height = Spinbox(frm_entry, width=3, from_=1, to=500, command=self.set_model_height)
        self.ctl_height.bind("<Return>", self.set_model_height)
        self.ctl_height.pack(side='left')
        CreateToolTip(self.ctl_height, "Height highly correlates with age, ideal body weight and body surface area")

        self.ctl_use_ibw = IntVar()  # No real body weight
        self.ctl_use_ibw.set(1)
        self.ctl_use_ibw_cb = Checkbutton(frm_entry, variable=self.ctl_use_ibw, onvalue=1, offvalue=0, text="Use IBW", command=self.set_use_ibw)
        self.ctl_use_ibw_cb.pack(side='left')
        CreateToolTip(self.ctl_use_ibw_cb, "Estimate ideal body weight from height")

        self.lbl_weight = Label(frm_entry, text='Weight, kg')
        self.lbl_weight.pack(side='left')
        CreateToolTip(self.lbl_weight, "Real body weight")
        self.ctl_weight = Spinbox(frm_entry, width=4, from_=1, to=500, command=self.set_model_weight)
        self.ctl_weight.bind("<Return>", self.set_model_weight)
        self.ctl_weight.pack(side='left')

        Label(frm_entry, text='Body temp, °C').pack(side='left')
        self.ctl_sbx_temp = Spinbox(frm_entry, width=4, from_=0.0, to=50.0,
            format='%.1f',
            increment=0.1,
         command=self.set_model_body_temp)
        self.ctl_sbx_temp.bind("<Return>", self.set_model_body_temp)
        self.ctl_sbx_temp.pack(side='left')
        CreateToolTip(self.ctl_sbx_temp, "Axillary temperature, used for perspiration evaluation")

        reset = Button(frm_entry, text="Reset", command=self.set_input_defaults)
        reset.pack(side='left')
        CreateToolTip(reset, "Drop changes for sex, height, real body weight, temp")

    def set_input_defaults(self, event=None):
        self.ctl_sex.current(0)
        self.set_model_sex()

        self.ctl_height.delete(0, 'end')
        self.ctl_height.insert(0, 186)  # cm
        self.set_model_height()

        # Can't change widget value while it being disabled, so here is a trick
        self.ctl_weight['state'] = NORMAL
        self.ctl_weight.delete(0, 'end')
        self.ctl_weight.insert(0, 55)  # kg
        self.ctl_weight['state'] = self.lbl_weight['state']
        self.set_model_weight()

        self.ctl_use_ibw.set(1)
        self.set_use_ibw()

        self.ctl_sbx_temp.delete(0, 'end')
        self.ctl_sbx_temp.insert(0, 36.6)  # celsus degrees
        self.set_model_body_temp()

    def set_model_sex(self, event=None):
        self.HModel.sex = self.ctl_sex.get().lower()
        self.print()

    def set_model_height(self, event=None):
        self.HModel.height = float(self.ctl_height.get()) / 100
        self.print()

    def set_model_weight(self, event=None):
        self.HModel.weight = float(self.ctl_weight.get())
        self.print()

    def set_model_body_temp(self, event=None):
        self.HModel.body_temp = float(self.ctl_sbx_temp.get())
        self.print()

    def set_use_ibw(self, event=None):
        if self.ctl_use_ibw.get() == 0:
            self.lbl_weight['state'] = NORMAL
            self.ctl_weight['state'] = NORMAL
            self.HModel.use_ibw(False)
        else:
            self.lbl_weight['state'] = DISABLED
            self.ctl_weight['state'] = DISABLED
            self.HModel.use_ibw(True)
        self.print()

    def print(self, event=None):
        """Calculate and print some evaluated data."""
        self.TxtView.set_text("{}\n--- Drugs --------------------------------------\n{}".format(str(self.HModel), self.HModel.medication()))


class TextView(Frame):
    def __init__(self, parent=None):
        super(TextView, self).__init__()
        self.parent = parent

        # Could be replaced with tkinter.scrolledtext
        # self.frm_txt = scrolledtext.ScrolledText(self.root, undo=True)
        # self.txt.config(font=('consolas', 10), undo=True, wrap='word')
        # self.frm_txt.pack(expand=True, fill=BOTH)
        frm_txt = Frame(self, width=450, height=300)
        frm_txt.pack(fill=BOTH, expand=True)
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

        # Context menu
        self.popup_menu = Menu(self, tearoff=False)
        self.popup_menu.add_command(label="Select all", command=self.select_all, accelerator="Ctrl+A")
        self.txt.bind("<Button-3>", self.popup)

    def popup(self, event):
        self.popup_menu.post(event.x_root, event.y_root)

    def set_text(self, text):
        """Replace current text in TextView."""
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

    # def copy_text(self):    
    #     self.clipboard_clear()
    #     self.clipboard_append(text)


class ABGInterpreter(Frame):
    def __init__(self, parent=None):
        super(ABGInterpreter, self).__init__()
        self.parent = parent
        # Create columns of widgets for ABG input
        frm_entry = Frame(self)
        frm_entry.pack(fill=BOTH)  # Aligns to left (not TOP center) somehow

        Label(frm_entry, text='pH').grid(row=1, column=0)
        self.sbx_pH = Spinbox(frm_entry, width=4, from_=0, to=14,
            format='%.2f',
            increment=0.01,
            command=self.print)
        self.sbx_pH.bind("<Return>", self.print)
        self.sbx_pH.grid(row=1, column=1)  # Default pH 7.40

        Label(frm_entry, text='pCO2, mmHg').grid(row=2, column=0)
        self.sbx_pCO2 = Spinbox(frm_entry, width=4, from_=0.0, to=150.0,
            format='%.1f',
            increment=0.1,
            command=self.print)
        self.sbx_pCO2.bind("<Return>", self.print)
        self.sbx_pCO2.grid(row=2, column=1)  # Default pCO2 40.0 mmHg

        self.txt = scrolledtext.ScrolledText(self)
        self.txt.config(font=('consolas', 10), undo=True, wrap='word')
        self.txt.pack(expand=True, fill=BOTH)

        button = Button(frm_entry, text="Reset", command=self.set_defaults)
        button.grid(row=2, column=2)

        self.set_defaults()

    def set_defaults(self):
        self.sbx_pH.delete(0, END)
        self.sbx_pH.insert(0, '7.40')  # cm
        self.sbx_pCO2.delete(0, END)
        self.sbx_pCO2.insert(0, 40.0)  # kg
        self.print()

    def print(self, event=None):
        pH = float(self.sbx_pH.get())
        pCO2 = float(self.sbx_pCO2.get())
        info = textwrap.dedent("""\
        pCO2    {:2.1f} kPa
        HCO3(P) {:2.1f} mmol/L
        SBE     {:2.1f} mEq/L
        Result: {}""".format(
            pCO2 * 0.133322368,
            abg.calculate_hco3p(pH, pCO2 * 0.133322368),  # to kPa
            abg.calculate_cbase(pH, pCO2 * 0.133322368),
            abg.abg(pH, pCO2)))
        self.txt['state'] = NORMAL
        self.txt.delete(1.0, END)
        self.txt.insert(END, info)
        self.txt['state'] = DISABLED


class CalcElectrolytes(Frame):
    def __init__(self, parent=None):
        super(CalcElectrolytes, self).__init__()
        self.parent = parent
        # Create columns of widgets for input
        frm_entry = Frame(self)
        frm_entry.pack(fill=BOTH)  # Aligns to left (not TOP center) somehow

        Label(frm_entry, text='K, mmol/L').grid(row=1, column=0)
        self.sbx_K = Spinbox(frm_entry, width=3, from_=0, to=15,
            format='%2.1f',
            increment=0.1,
            command=self.print)
        self.sbx_K.grid(row=1, column=1)

        Label(frm_entry, text='Na, mmol/L').grid(row=2, column=0)
        self.sbx_Na = Spinbox(frm_entry, width=3, from_=0.0, to=200.0,
            format='%3.0f',
            increment=1,
            command=self.print)
        self.sbx_Na.grid(row=2, column=1)

        Label(frm_entry, text='Cl, mmol/L').grid(row=3, column=0)
        self.sbx_Cl = Spinbox(frm_entry, width=3, from_=0.0, to=200.0,
            format='%3.0f',
            increment=1,
            command=self.print)
        self.sbx_Cl.grid(row=3, column=1)

        self.txt = scrolledtext.ScrolledText(self)
        self.txt.config(font=('consolas', 10), undo=True, wrap='word')
        self.txt.pack(expand=True, fill=BOTH)

        button = Button(frm_entry, text="Reset", command=self.set_defaults)
        button.grid(row=1, column=2)

        self.set_defaults()

    def set_defaults(self):
        self.sbx_K.delete(0, END)
        self.sbx_K.insert(0, 4.0)
        self.sbx_Na.delete(0, END)
        self.sbx_Na.insert(0, 145)
        self.sbx_Cl.delete(0, END)
        self.sbx_Cl.insert(0, 95)
        self.print()

    def print(self, event=None):
        # pH = float(self.sbx_pH.get())
        # pCO2 = float(self.sbx_pCO2.get())
        # info = textwrap.dedent("""\
        # pCO2    {:2.1f} kPa
        # HCO3(P) {:2.1f} mmol/L
        # SBE     {:2.1f} mEq/L
        # Result: {}""".format(
        #     pCO2 * 0.133322368,
        #     abg.calculate_hco3p(pH, pCO2 * 0.133322368),  # to kPa
        #     abg.calculate_cbase(pH, pCO2 * 0.133322368),
        #     abg.abg(pH, pCO2)))
        info = "NotImplementedYet"
        self.txt['state'] = NORMAL
        self.txt.delete(1.0, END)
        self.txt.insert(END, info)
        self.txt['state'] = DISABLED


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
        label = Label(self.tw, text=self.text, justify='left',
            background="#ffffff", relief='solid', borderwidth=1,
            wraplength=self.wraplength)
        label.pack(ipadx=1)

    def hidetip(self):
        tw, self.tw = self.tw, None
        if tw:
            tw.destroy()


def main():
    root = MainWindow()
    root.mainloop()


if __name__ == '__main__':
    main()
