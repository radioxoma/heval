#!/usr/bin/env python

"""Heval tkinter-based GUI.

Author: Eugene Dvoretsky
"""

from __future__ import annotations

import random
import textwrap
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

import tkinterweb

import heval
from heval import abg, common, human

__css__ = """
<style>
  abbr { border-bottom: 1px dotted; }
</style>
"""


class SpinboxFloat(ttk.Spinbox):
    """Spinbox widget with float (dot separator) or empty input allowed.

    https://stackoverflow.com/questions/4140437/interactively-validating-entry-widget-content-in-tkinter
    """

    def __init__(self, parent=None, **kw):
        super().__init__(parent, **kw)
        self.parent = parent
        ctl_sbx_validator = self.register(self.is_empty_or_float)
        self["validate"] = "key"
        self["validatecommand"] = (ctl_sbx_validator, "%P")

    def is_empty_or_float(self, value: str) -> bool:
        """Allow empty value or something castable to float."""
        if value == "":
            return True
        try:
            float(value)
            return True
        except ValueError:
            self.bell()
            return False


class TextHtmlView(tkinterweb.HtmlFrame):
    """Default HTML widget to show formatted text with tooltips."""

    def __init__(self, parent=None, *args, **kwargs):
        super().__init__(parent, *args, messages_enabled=False, **kwargs)
        self.parent = parent
        # Tooltips on click, not hover
        self.bind("<Button-1>", self._show_tooltip)
        # self.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def set_text(self, text: str):
        """Set preformatted text to show it as <code> block."""
        text = text.replace("\n", "&nbsp;<br>")
        self.load_html(__css__ + f"<code>{text}</code>")

    def set_html(self, html: str):
        """Set HTML code as is."""
        self.load_html(__css__ + html)

    def _show_tooltip(self, event):
        element = self.get_currently_hovered_element()
        title = element.getAttribute("title")
        if title:
            menu = tk.Menu(self.parent, tearoff=False)
            menu.add_command(label=title)
            menu.tk_popup(event.x_root, event.y_root, 0)


class ScrolledText(tk.Text):
    """Clone of the standard `tkinter.scrolledtext` built with ttk widgets."""

    def __init__(self, parent=None, **kw):
        self.frame = ttk.Frame(parent)
        self.vbar = ttk.Scrollbar(self.frame)
        self.vbar.pack(side=tk.RIGHT, fill=tk.Y)
        kw.update({"yscrollcommand": self.vbar.set})
        super().__init__(self.frame, **kw)

        self.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.vbar["command"] = self.yview

        # Copy geometry methods of self.frame without overriding Text
        # methods -- hack!
        text_meths = vars(tk.Text).keys()
        methods = vars(tk.Pack).keys() | vars(tk.Grid).keys() | vars(tk.Place).keys()
        methods = methods.difference(text_meths)

        for m in methods:
            if m[0] != "_" and m != "config" and m != "configure":
                setattr(self, m, getattr(self.frame, m))

    def __str__(self):
        return str(self.frame)


class TextView(ScrolledText):
    """Read only text widget with hotkeys."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config(font="TkFixedFont", wrap=tk.WORD)
        self.popup_menu = tk.Menu(self, tearoff=False)
        self.popup_menu.add_command(
            label="Copy", command=self.copy, accelerator="Ctrl+C"
        )
        self.popup_menu.add_command(label="Copy all", command=self.copy_all)
        self.popup_menu.add_command(
            label="Select all", command=self.select_all, accelerator="Ctrl+A"
        )
        self.bind("<Control-c>", self.copy)  # Lowercase for Linux
        self.bind("<Control-a>", self.select_all)
        self.bind("<ButtonRelease-3>", self.popup)
        # Make key bindings work again in disabled tk.Text widget under Linux
        self.bind("<ButtonRelease-1>", lambda event: self.focus_set())

    def popup(self, event):
        self.popup_menu.tk_popup(event.x_root, event.y_root)

    def set_text(self, text):
        """Replace current text."""
        self["state"] = tk.NORMAL
        self.delete(1.0, tk.END)
        self.insert(tk.END, text)
        # Linux can't catch keypress when disabled, Use `focus_set` as workaround
        self["state"] = tk.DISABLED

    def select_all(self, event=None):
        self.tag_add(tk.SEL, "1.0", tk.END)
        self.mark_set(tk.INSERT, "1.0")
        self.see(tk.INSERT)
        return "break"

    def copy(self, event=None):
        if self.tag_ranges("sel"):
            self.clipboard_clear()
            self.clipboard_append(self.get(tk.SEL_FIRST, tk.SEL_LAST))
            self.update()  # Force copy on Windows

    def copy_all(self, event=None):
        self.clipboard_clear()
        self.clipboard_append(self.get(1.0, tk.END))


class TextViewCustom(ttk.Frame):
    """Alternate implementation of ScrolledText."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

        frm_txt = ttk.Frame(self, width=450, height=300)
        frm_txt.pack(expand=True, fill=tk.BOTH)
        frm_txt.grid_propagate(False)  # ensure a consistent GUI size
        frm_txt.grid_rowconfigure(0, weight=1)
        frm_txt.grid_columnconfigure(0, weight=1)  # implement stretchability

        self.txt = tk.Text(frm_txt, borderwidth=1, relief=tk.FLAT)
        self.txt.config(undo=True, wrap="word")
        self.txt.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        # Create a Scrollbar and associate it with txt
        scrollb = ttk.Scrollbar(frm_txt, command=self.txt.yview)
        scrollb.grid(row=0, column=1, sticky="nsew")
        self.txt["yscrollcommand"] = scrollb.set

    def set_text(self, text):
        """Replace current text."""
        self.txt["state"] = tk.NORMAL
        self.txt.delete(1.0, tk.END)
        self.txt.insert(tk.END, text)
        self.txt["state"] = tk.DISABLED

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
        self.txt.tag_add(tk.SEL, "1.0", tk.END)
        self.txt.mark_set(tk.INSERT, "1.0")
        self.txt.see(tk.INSERT)
        return "break"


class MainWindow(ttk.Frame):
    def __init__(self, parent: tk.Tk, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent
        self.parent.title("Heval: the human evaluator — v" + heval.__version__)
        self.parent.geometry("650x590")

        style = ttk.Style()
        style.theme_use("clam")  # ('clam', 'alt', 'default', 'classic')
        style.configure("TButton", padding=2)
        style.configure("TMenubutton", padding=2, width=6)  # Otherwise too big on Linux
        self.adjust_font_size()

        self.human = human.HumanModel()

        menubar = tk.Menu(self.parent)  # Conventional name
        menu_file = tk.Menu(menubar, tearoff=False)
        menu_file.add_command(
            label="Exit", command=self.parent.destroy, accelerator="Esc"
        )
        menubar.add_cascade(label="File", menu=menu_file)

        menu_view = tk.Menu(menubar, tearoff=False)
        self._verbose = tk.BooleanVar()
        self._verbose.set(self.human.verbose)
        # tooltip="Show normally hidden extra messages in report texts"
        menu_view.add_checkbutton(
            label="Verbose report",
            command=self.set_model_verbose,
            variable=self._verbose,
            accelerator="v",
        )
        menu_view.add_command(
            label="Increase font size",
            command=lambda: self.adjust_font_size("increase"),
            accelerator="Ctrl++",
        )
        menu_view.add_command(
            label="Decrease font size",
            command=lambda: self.adjust_font_size("decrease"),
            accelerator="Ctrl+-",
        )
        menu_view.add_command(
            label="Default font size",
            command=lambda: self.adjust_font_size(),
            accelerator="Ctrl+0",
        )
        menubar.add_cascade(label="View", menu=menu_view)

        menu_about = tk.Menu(menubar, tearoff=False, name="help")
        # tooltip="Read short usage manual"
        menu_about.add_command(
            label="Help", command=lambda: HelpWindow(self.parent), accelerator="F1"
        )
        # tooltip="Visit Heval's website for updates and additional documentation"
        menu_about.add_command(label="Website and updates", command=visit_website)
        menu_about.add_command(
            label="About...", command=lambda: AboutWindow(self.parent)
        )
        menubar.add_cascade(label="Help", menu=menu_about)
        self.parent["menu"] = menubar

        # START INPUT SECTION
        fr_entry = ttk.Frame(self)
        fr_entry.pack(anchor=tk.W)
        ttk.Label(fr_entry, text="Sex").pack(side=tk.LEFT)
        self._var_sex = tk.StringVar()
        self.sex_list = [sex.title() for sex in common.HumanSex.__members__.keys()]
        self.ctl_sex = ttk.OptionMenu(
            fr_entry,
            self._var_sex,
            self.sex_list[0],
            *self.sex_list,
            command=self.set_model_sex,
        )
        self.ctl_sex.pack(side=tk.LEFT)
        CreateToolTip(
            self.ctl_sex,
            "Age and sex selector. Calculations quite differ for adults and children",
        )

        ttk.Label(fr_entry, text="Height, cm").pack(side=tk.LEFT)
        self.ctl_sbx_height = SpinboxFloat(
            fr_entry, width=3, from_=1, to=500, command=self.set_model_height
        )
        self.ctl_sbx_height.bind("<KeyRelease>", self.set_model_height)
        self.ctl_sbx_height.pack(side=tk.LEFT)
        CreateToolTip(
            self.ctl_sbx_height,
            "Height highly correlates with age, ideal body weight and body surface area",
        )

        self._var_use_ibw = tk.IntVar()  # No real body weight
        self._var_use_ibw.set(1)
        self.ctl_use_ibw_cb = ttk.Checkbutton(
            fr_entry,
            variable=self._var_use_ibw,
            onvalue=1,
            offvalue=0,
            text="Use IBW",
            command=self.set_model_use_ibw,
        )
        self.ctl_use_ibw_cb.pack(side=tk.LEFT)
        CreateToolTip(
            self.ctl_use_ibw_cb,
            "Estimate ideal body weight from height\nand use IBW instead RBW in all calculations",
        )

        self.lbl_weight = ttk.Label(fr_entry, text="Weight, kg")
        self.lbl_weight.pack(side=tk.LEFT)
        self.ctl_sbx_weight = SpinboxFloat(
            fr_entry,
            width=4,
            from_=1,
            to=500,
            format="%.1f",
            increment=1,
            command=self.set_model_weight,
        )
        self.ctl_sbx_weight.bind("<KeyRelease>", self.set_model_weight)
        self.ctl_sbx_weight.pack(side=tk.LEFT)
        CreateToolTip(self.ctl_sbx_weight, "Real body weight")

        ttk.Label(fr_entry, text="Age, years").pack(side=tk.LEFT)
        self.ctl_sbx_age = SpinboxFloat(
            fr_entry,
            width=3,
            from_=0.0,
            to=200.0,
            format="%1.0f",
            increment=1,
            command=self.set_model_age,
        )
        self.ctl_sbx_age.bind("<KeyRelease>", self.set_model_age)
        self.ctl_sbx_age.pack(side=tk.LEFT)
        CreateToolTip(self.ctl_sbx_age, "Human age, years")

        ttk.Label(fr_entry, text="Body temp, °C").pack(side=tk.LEFT)
        self.ctl_sbx_temp = SpinboxFloat(
            fr_entry,
            width=4,
            from_=0.0,
            to=50.0,
            format="%.1f",
            increment=0.1,
            command=self.set_model_body_temp,
        )
        self.ctl_sbx_temp.bind("<KeyRelease>", self.set_model_body_temp)
        self.ctl_sbx_temp.pack(side=tk.LEFT)
        CreateToolTip(
            self.ctl_sbx_temp, "Axillary temperature, used for perspiration evaluation"
        )

        reset = ttk.Button(fr_entry, text="Reset", command=self.set_input_defaults)
        reset.pack(side=tk.LEFT)
        CreateToolTip(
            reset, "Set default values for sex, height, real body weight, temp"
        )
        # END INPUT SECTION
        self.set_input_defaults()

        nb = tkinterweb.Notebook(self)
        self.CMain = CalcMain(nb, self.human)
        self.CNutrition = CalcNutrition(nb, self.human)
        self.CElectrolytes = CalcElectrolytes(nb, self.human)
        nb.add(self.CMain, text="Human body")
        nb.add(self.CNutrition, text="Nutrition")
        nb.add(self.CElectrolytes, text="Laboratory")
        nb.pack(expand=True, fill=tk.BOTH)  # BOTH looks less ugly under Windows

        self.parent.bind("<Escape>", lambda e: self.parent.destroy())
        self.bind_all("<F1>", lambda e: HelpWindow(self.parent))
        self.bind_all("<v>", self.set_model_verbose)
        self.bind_all(
            "<Control-Key-equal>", lambda e: self.adjust_font_size("increase")
        )
        self.bind_all(
            "<Control-Key-minus>", lambda e: self.adjust_font_size("decrease")
        )
        self.bind_all("<Control-Key-0>", lambda e: self.adjust_font_size())
        # self.bind('<r>', lambda e: self.set_input_defaults())
        self.parent.bind("<Alt-KeyPress-1>", lambda e: nb.select(0))
        self.parent.bind("<Alt-KeyPress-2>", lambda e: nb.select(1))
        self.parent.bind("<Alt-KeyPress-3>", lambda e: nb.select(2))
        self.bind_all("<<HumanModelChanged>>", self.eval)
        self.bind_all("<<HumanModelChanged>>", self.CMain.eval, add="+")
        self.bind_all("<<HumanModelChanged>>", self.CNutrition.eval, add="+")
        self.bind_all("<<HumanModelChanged>>", self.CElectrolytes.eval, add="+")

        # self.statusbar_str = StringVar()
        # self.statusbar_str.set("Hello world!")
        # statusbar = Label(self, textvariable=self.statusbar_str, relief=SUNKEN, anchor=W)
        # statusbar.pack(side=BOTTOM, fill=X)

    def set_input_defaults(self, event=None):
        self._var_sex.set(self.sex_list[0])
        self.set_model_sex()

        self.ctl_sbx_height.delete(0, tk.END)
        self.ctl_sbx_height.insert(0, "177")  # cm
        self.set_model_height()

        # Can't change widget value while it being disabled, so here is a trick
        self.ctl_sbx_weight["state"] = tk.NORMAL
        self.ctl_sbx_weight.delete(0, tk.END)
        self.ctl_sbx_weight.insert(0, "69.0")  # kg
        self.ctl_sbx_weight["state"] = self.lbl_weight["state"]
        self.set_model_weight()

        self._var_use_ibw.set(1)
        self.set_model_use_ibw()

        self.ctl_sbx_age.delete(0, tk.END)
        self.ctl_sbx_age.insert(0, "40")
        self.set_model_age()

        self.ctl_sbx_temp.delete(0, tk.END)
        self.ctl_sbx_temp.insert(0, "36.6")  # celsus degrees
        self.set_model_body_temp()

    def adjust_font_size(self, event=None):
        """Set default font size or adjust current size.

        Bug 1. Detect actual monospaced font name and hardcode size to 9
        on Windows it's Courier new 10pt, on Linux DejaVu Sans Mono 9 pt

        Bug 2. Must be called once on __init__ without parameters, because
        `some_font['size']` has negative value by default.
        """
        for font in ("TkDefaultFont", "TkTextFont", "TkFixedFont", "TkMenuFont"):
            font_obj = tkfont.nametofont(font)
            # print(font_obj.actual())
            # font_obj = font.Font(font=font)
            if event == "increase":
                font_obj["size"] += 1
            elif event == "decrease":
                if font_obj["size"] > 2:
                    font_obj["size"] -= 1
            else:  # Set default font size
                font_obj["size"] = 9

    def set_model_sex(self, event=None):
        self.human.body_sex = common.HumanSex[self._var_sex.get().upper()]
        self.event_generate("<<HumanModelChanged>>")

    def set_model_height(self, event=None):
        self.human.body_height = float(self.ctl_sbx_height.get()) / 100
        self.event_generate("<<HumanModelChanged>>")

    def set_model_weight(self, event=None):
        self.human.body_weight = float(self.ctl_sbx_weight.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_age(self, event=None):
        self.human.body_age = float(self.ctl_sbx_age.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_body_temp(self, event=None):
        self.human.body_temp = float(self.ctl_sbx_temp.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_use_ibw(self, event=None):
        if self._var_use_ibw.get() == 0:
            self.human.body_use_ibw = False
            self.lbl_weight["state"] = tk.NORMAL
            self.ctl_sbx_weight["state"] = tk.NORMAL
        else:
            self.human.body_use_ibw = True
            self.ctl_sbx_weight.delete(0, tk.END)
            self.ctl_sbx_weight.insert(0, f"{self.human.body_weight:.1f}")
            self.ctl_sbx_weight["state"] = tk.DISABLED
            self.lbl_weight["state"] = tk.DISABLED
        self.event_generate("<<HumanModelChanged>>")

    def set_model_verbose(self, event=None):
        self.human.verbose = not self.human.verbose  # Invert boolean
        self._verbose.set(self.human.verbose)  # Change flag in menu accordingly
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        """Update GUI."""
        if self.human.body_use_ibw:
            self.ctl_sbx_weight["state"] = tk.NORMAL
            self.ctl_sbx_weight.delete(0, tk.END)
            self.ctl_sbx_weight.insert(0, f"{self.human.body_weight:.1f}")
            self.ctl_sbx_weight["state"] = self.lbl_weight["state"]


class HelpWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        x = self.parent.winfo_x()
        y = self.parent.winfo_y()
        self.geometry(f"+{x + 50:d}+{y + 100:d}")
        self.title("Help")

        # Mimic Label colors
        lbl_bg = ttk.Style().lookup("TLabel", "background")
        # lbl_font = ttk.Style().lookup("TLabel", "font")  # TkDefaultFont
        self.configure(bg=lbl_bg)

        self.text = TextHtmlView(self)
        self.text.set_html(heval.__doc__)
        self.text.pack(expand=True, fill=tk.BOTH)

        self.ctl_frame = ttk.Frame(self, padding=8)
        self.ctl_btn_close = ttk.Button(
            self.ctl_frame, text="Close", command=self.destroy
        )
        self.ctl_btn_close_tip = None
        self.ctl_btn_close.bind("<Leave>", self.update_tooltip, add="+")
        self.ctl_btn_close.pack(side=tk.RIGHT)
        self.ctl_frame.pack(fill=tk.BOTH)
        self.bind("<Escape>", lambda event: self.destroy())

    def update_tooltip(self, event=None):
        """Show egg only if mouse pointed twice."""
        info = "⚫ " + magic8ball()
        if self.ctl_btn_close_tip:
            self.ctl_btn_close_tip.text = info
            # self.ctl_btn_close['text'] = info
        else:
            self.ctl_btn_close_tip = CreateToolTip(self.ctl_btn_close, info, delay=1500)


class AboutWindow(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        x = self.parent.winfo_x()
        y = self.parent.winfo_y()
        self.geometry(f"+{x + 50:d}+{y + 100:d}")
        self.title("About v" + heval.__version__)

        self.text = TextHtmlView(self)
        self.text.set_html(heval.DISCLAIMER)
        self.text.pack(expand=True, fill=tk.BOTH)

        self.ctl_frame = ttk.Frame(self, padding=8)
        self.ctl_btn_website = ttk.Button(
            self.ctl_frame, text="Visit website", command=visit_website
        )
        CreateToolTip(self.ctl_btn_website, "Source code, docs and updates")
        self.ctl_btn_close = ttk.Button(
            self.ctl_frame, text="Close", command=self.destroy
        )
        self.ctl_btn_close.pack(side=tk.RIGHT)
        self.ctl_btn_website.pack(side=tk.RIGHT)
        self.ctl_frame.pack(fill=tk.BOTH)
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()


class CalcMain(ttk.Frame):
    def __init__(self, parent, human_model):
        super().__init__(parent)
        self.parent = parent
        self.human = human_model

        self.TxtView = TextHtmlView(self)
        self.TxtView.pack(expand=True, fill=tk.BOTH)
        self.TxtView.set_text(
            textwrap.dedent(
                """\
        Just set sex and height. Open \"Help\" from menu or by pressing F1 key.

        Не знаете с чего начать? Выберите \"Help\" в меню, чтобы вызвать краткую справку на русском языке. Или просто нажмите клавишу F1.
        """
            )
        )

    def eval(self, event=None):
        """Calculate and print some evaluated data."""
        self.human.init()
        self.TxtView.set_text(self.human.eval_body())


class CalcNutrition(ttk.Frame):
    def __init__(self, parent, human_model):
        super().__init__(parent)
        self.parent = parent
        self.human = human_model

        fr_entry = ttk.Frame(self)
        fr_entry.pack(anchor=tk.W)

        self.var_rbtm_calc_method = tk.IntVar()
        self.var_rbtm_calc_method.set(0)

        # Fluid input
        fr_fluid_entry = ttk.LabelFrame(fr_entry, text="Daily fluid")
        fr_fluid_entry.pack(side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH)

        ctl_btn_fluid = ttk.Button(
            fr_fluid_entry, text="Reset", command=self.set_input_fluid_defaults
        )
        # CreateToolTip(ctl_btn_fluid, "Reset fluid")
        ctl_btn_fluid.grid(row=0, column=0)

        ttk.Label(fr_fluid_entry, text="ml/kg/24h").grid(row=1, column=0)
        self.ctl_sbx_fluid_mul = SpinboxFloat(
            fr_fluid_entry,
            width=3,
            from_=0.0,
            to=200.0,
            format="%1.0f",
            increment=1,
            command=self.set_model_fluid_multiplier,
        )
        self.ctl_sbx_fluid_mul.bind("<KeyRelease>", self.set_model_fluid_multiplier)
        self.ctl_sbx_fluid_mul.grid(row=1, column=1)
        CreateToolTip(
            self.ctl_sbx_fluid_mul,
            "24 hours fluid demand.\nTypical 30-35 ml/kg for an adult. Much higher for children.",
        )

        ttk.Label(fr_fluid_entry, text="ml/24h").grid(row=2, column=0)
        self.lbl_fluid_24h = ttk.Label(fr_fluid_entry)
        self.lbl_fluid_24h.grid(row=2, column=1)

        # Kcal input
        self.fr_kcal_entry = ttk.LabelFrame(fr_entry, text="By calorie demand")
        self.fr_kcal_entry.pack(side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH)

        ctl_btn_kcal = ttk.Button(
            self.fr_kcal_entry, text="Reset", command=self.set_input_kcal_defaults
        )
        # CreateToolTip(ctl_btn_kcal, "Reset kcal")
        ctl_btn_kcal.grid(row=0, column=0)

        ctl_rbtn0_method = ttk.Radiobutton(
            self.fr_kcal_entry,
            text="",
            variable=self.var_rbtm_calc_method,
            value=0,
            command=self.set_nutr_gui_state,
        )
        ctl_rbtn0_method.grid(row=0, column=1)
        CreateToolTip(
            ctl_rbtn0_method,
            "Calculate daily nutrition dose by calorie (not protein) requirement",
        )

        ttk.Label(self.fr_kcal_entry, text="kcal/kg/24h").grid(row=1, column=0)
        self.ctl_sbx_kcal_mul = SpinboxFloat(
            self.fr_kcal_entry,
            width=2,
            from_=0.0,
            to=99.0,
            format="%1.0f",
            increment=1,
            command=self.set_model_kcal_multiplier,
        )
        self.ctl_sbx_kcal_mul.bind("<KeyRelease>", self.set_model_kcal_multiplier)
        self.ctl_sbx_kcal_mul.grid(row=1, column=1)
        CreateToolTip(
            self.ctl_sbx_kcal_mul, "24 hours energy demand.\nTypical 25-30 kcal/kg."
        )

        ttk.Label(self.fr_kcal_entry, text="kcal/24h").grid(row=2, column=0)
        self.lbl_kcal_24h = ttk.Label(self.fr_kcal_entry)
        self.lbl_kcal_24h.grid(row=2, column=1)

        # Protein & Nitrogen balance input
        self.fr_nitrogen_entry = ttk.LabelFrame(fr_entry, text="By nitrogen balance")
        self.fr_nitrogen_entry.pack(
            side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH
        )

        ctl_btn_prot = ttk.Button(
            self.fr_nitrogen_entry,
            text="Reset",
            command=self.set_input_protein_defaults,
        )
        # CreateToolTip(ctl_btn_prot, "Reset protein")
        ctl_btn_prot.grid(row=0, column=0)

        ctl_rbtn1_method = ttk.Radiobutton(
            self.fr_nitrogen_entry,
            text="",
            variable=self.var_rbtm_calc_method,
            value=1,
            command=self.set_nutr_gui_state,
        )
        ctl_rbtn1_method.grid(row=0, column=1)
        CreateToolTip(
            ctl_rbtn1_method,
            "Calculate daily nutrition dose by measured protein (not calorie) requirement",
        )

        ttk.Label(self.fr_nitrogen_entry, text="Urine urea, mmol/24h").grid(
            row=1, column=0
        )
        self.ctl_sbx_uurea = SpinboxFloat(
            self.fr_nitrogen_entry,
            width=4,
            from_=0.0,
            to=9999.0,
            format="%.0f",
            increment=10,
            command=self.set_model_uurea,
        )
        self.ctl_sbx_uurea.bind("<KeyRelease>", self.set_model_uurea)
        self.ctl_sbx_uurea.grid(row=1, column=1)
        CreateToolTip(
            self.ctl_sbx_uurea,
            "Urine urea excreted during 24h (equals to total urea nitrogen, when measured in mmol/24h)",
        )

        ttk.Label(self.fr_nitrogen_entry, text="Protein g/24h").grid(row=2, column=0)
        self.lbl_prot_24h = ttk.Label(self.fr_nitrogen_entry)
        self.lbl_prot_24h.grid(row=2, column=1)
        CreateToolTip(
            self.lbl_prot_24h,
            "24h protein intake needed to maintain zero nitrogen balance",
        )

        ttk.Label(self.fr_nitrogen_entry, text="Protein, g/kg/24h").grid(
            row=3, column=0
        )
        # self.ctl_sbx_prot_g_kg_24h = SpinboxFloat(
        #     self.fr_nitrogen_entry, width=4, from_=0.0, to=10.0,
        #     format='%.2f', increment=0.1, command=self.increment_uurea_widget)
        # self.ctl_sbx_prot_g_kg_24h.bind("<KeyRelease>", self.eval)
        # self.ctl_sbx_prot_g_kg_24h.grid(row=2, column=1)
        # CreateToolTip(self.ctl_sbx_prot_g_kg_24h, "Urine urea concentration in 24h sample")
        self.lbl_sbx_prot_g_kg_24h = ttk.Label(self.fr_nitrogen_entry)
        self.lbl_sbx_prot_g_kg_24h.grid(row=3, column=1)

        self.TxtView = TextHtmlView(self)
        self.TxtView.pack(expand=True, fill=tk.BOTH)
        self.set_input_fluid_defaults()
        self.set_input_kcal_defaults()
        self.set_input_protein_defaults()
        self.set_nutr_gui_state()
        self.TxtView.set_text(
            textwrap.dedent(
                """\
            Just set sex and height.

            Nutrition mixtures dosage can be estimated in two ways:
              * As daily calorie goal by weight (kcal/kg/24h)
              * As daily protein goal by nitrogen balance (urea nitrogen loss mmol/24h) or expected protein demand (g/kg/24h) which are dependent on each other

            Heval will suggest additional fluid if nutrition mixture doesn't contain full 24h volume. Negative value means fluid excess.
            """
            )
        )

    def set_input_fluid_defaults(self, event=None):
        self.ctl_sbx_fluid_mul.delete(0, tk.END)
        self.ctl_sbx_fluid_mul.insert(0, "30")  # ml/kg/24h
        self.set_model_fluid_multiplier()

    def set_input_kcal_defaults(self, event=None):
        self.ctl_sbx_kcal_mul.delete(0, tk.END)
        self.ctl_sbx_kcal_mul.insert(0, "25")  # kcal/kg/24h
        self.set_model_kcal_multiplier()

    def set_input_protein_defaults(self, event=None):
        self.ctl_sbx_uurea.delete(0, tk.END)
        self.ctl_sbx_uurea.insert(0, "190")  # Corresponds to 0.8 g/kg/24h
        self.set_model_uurea()

    def set_nutr_gui_state(self, event=None):
        def set_state(widget, state):
            # Set all subwidgets state NORMAL, DISABLED
            for child in widget.winfo_children():
                if not isinstance(child, ttk.Radiobutton):
                    child.configure(state=state)

        if self.var_rbtm_calc_method.get() == 0:  # By kcal
            set_state(self.fr_kcal_entry, tk.NORMAL)
            set_state(self.fr_nitrogen_entry, tk.DISABLED)
        elif self.var_rbtm_calc_method.get() == 1:  # By UUN
            set_state(self.fr_kcal_entry, tk.DISABLED)
            set_state(self.fr_nitrogen_entry, tk.NORMAL)
        self.eval()

    def set_model_fluid_multiplier(self, event=None):
        self.human.nutrition.fluid_multiplier = float(self.ctl_sbx_fluid_mul.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_kcal_multiplier(self, event=None):
        self.human.nutrition.kcal_multiplier = float(self.ctl_sbx_kcal_mul.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_uurea(self, event=None):
        self.human.nutrition.uurea = float(self.ctl_sbx_uurea.get())
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        """Calculate and print some evaluated data."""
        self.lbl_fluid_24h["text"] = f"{self.human.nutrition.fluid_24h:.0f}"
        self.lbl_kcal_24h["text"] = f"{self.human.nutrition.kcal_24h:.0f}"
        self.lbl_prot_24h["text"] = f"{self.human.nutrition.uurea_prot_24h:.1f}"
        self.lbl_sbx_prot_g_kg_24h["text"] = (
            f"{self.human.nutrition.uures_prot_g_kg_24h:.2f}"
        )
        # self.ctl_sbx_prot_g_kg_24h.delete(0, tk.END)
        # self.ctl_sbx_prot_g_kg_24h.insert(0, f"{self.human_model.nutrition.uures_prot_g_kg_24h:.2f}")  # g/kg/24h
        info = list()
        if self.var_rbtm_calc_method.get() == 0:  # By kcal
            info.append(self.human.nutrition.describe_nutrition())
        elif self.var_rbtm_calc_method.get() == 1:  # By UUN
            info.append(self.human.nutrition.describe_nutrition(by_protein=True))
        self.TxtView.set_text("\n".join(info))


class CalcElectrolytes(ttk.Frame):
    def __init__(self, parent, human_model: human.HumanModel):
        super().__init__(parent)
        self.parent = parent
        self.human = human_model
        fr_entry = ttk.Frame(self)
        fr_entry.pack(anchor=tk.W)

        # ABG INPUT
        fr_abg_entry = ttk.LabelFrame(fr_entry, text="Basic ABG")
        fr_abg_entry.pack(side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH)

        ctl_btn_abg = ttk.Button(
            fr_abg_entry, text="Reset", command=self.set_input_abg_defaults
        )
        CreateToolTip(
            ctl_btn_abg, "Compare respiratory and metabolic impact on blood pH"
        )
        ctl_btn_abg.grid(row=1, column=0)

        ttk.Label(fr_abg_entry, text="pH").grid(row=2, column=0)
        self.ctl_sbx_pH = SpinboxFloat(
            fr_abg_entry,
            width=4,
            from_=0,
            to=14,
            format="%.2f",
            increment=0.01,
            command=self.set_model_pH,
        )
        self.ctl_sbx_pH.bind("<KeyRelease>", self.set_model_pH)
        self.ctl_sbx_pH.grid(row=2, column=1)

        ttk.Label(fr_abg_entry, text="pCO₂, mmHg").grid(row=3, column=0)
        self.ctl_sbx_pCO2 = SpinboxFloat(
            fr_abg_entry,
            width=4,
            from_=0.0,
            to=150.0,
            format="%.1f",
            increment=1,
            command=self.set_model_pCO2,
        )
        self.ctl_sbx_pCO2.bind("<KeyRelease>", self.set_model_pCO2)
        self.ctl_sbx_pCO2.grid(row=3, column=1)  # Default pCO2 40.0 mmHg

        ttk.Label(fr_abg_entry, text="HCO₃(P), mmol/L").grid(row=4, column=0)
        self.lbl_hco3 = ttk.Label(fr_abg_entry)
        CreateToolTip(self.lbl_hco3, "Actual bicarbonate")
        self.lbl_hco3.grid(row=4, column=1)

        # ELECTROLYTE INPUT
        fr_elec_entry = ttk.LabelFrame(fr_entry, text="Electrolytes")
        fr_elec_entry.pack(side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH)

        ctl_btn_elec = ttk.Button(
            fr_elec_entry, text="Reset", command=self.set_input_elec_defaults
        )
        CreateToolTip(
            ctl_btn_elec,
            "Find electrolyte imbalance and unmeasurable anion disturbances",
        )
        ctl_btn_elec.grid(row=1, column=0)

        ttk.Label(fr_elec_entry, text="K⁺, mmol/L").grid(row=2, column=0)
        self.ctl_sbx_K = SpinboxFloat(
            fr_elec_entry,
            width=3,
            from_=0,
            to=15,
            format="%2.1f",
            increment=0.1,
            command=self.set_model_K,
        )
        self.ctl_sbx_K.bind("<KeyRelease>", self.set_model_K)
        self.ctl_sbx_K.grid(row=2, column=1)

        ttk.Label(fr_elec_entry, text="Na⁺, mmol/L").grid(row=3, column=0)
        self.ctl_sbx_Na = SpinboxFloat(
            fr_elec_entry,
            width=3,
            from_=0.0,
            to=300.0,
            format="%3.0f",
            increment=1,
            command=self.set_model_Na,
        )
        CreateToolTip(
            self.ctl_sbx_Na, "Na⁺ and cGlu are used for serum osmolarity calculations"
        )
        self.ctl_sbx_Na.bind("<KeyRelease>", self.set_model_Na)
        self.ctl_sbx_Na.grid(row=3, column=1)

        ttk.Label(fr_elec_entry, text="Cl⁻, mmol/L").grid(row=4, column=0)
        self.ctl_sbx_Cl = SpinboxFloat(
            fr_elec_entry,
            width=3,
            from_=0.0,
            to=300.0,
            format="%3.0f",
            increment=1,
            command=self.set_model_Cl,
        )
        self.ctl_sbx_Cl.bind("<KeyRelease>", self.set_model_Cl)
        self.ctl_sbx_Cl.grid(row=4, column=1)

        # EXTRA INPUT
        fr_extra_entry = ttk.LabelFrame(fr_entry, text="Optional data")
        fr_extra_entry.pack(side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH)

        ctl_btn_elec = ttk.Button(
            fr_extra_entry, text="Reset", command=self.set_input_extra_defaults
        )
        CreateToolTip(ctl_btn_elec, "Tweak electrolyte calculations like a pro")
        ctl_btn_elec.grid(row=1, column=0)

        ttk.Label(fr_extra_entry, text="cGlu, mmol/L").grid(row=2, column=0)
        self.ctl_sbx_cGlu = SpinboxFloat(
            fr_extra_entry,
            width=4,
            from_=0,
            to=50,
            format="%.1f",
            increment=0.1,
            command=self.set_model_cGlu,
        )
        CreateToolTip(
            self.ctl_sbx_cGlu,
            "Enter glucose to properly calculate serum osmolarity (formula is '2Na⁺ + cGlu').\n\nIf patient blood contains other osmotically active molecules, such as ethanol or BUN (due to kidney damage), you shall add it manually or use lab osmometer.",
        )
        self.ctl_sbx_cGlu.bind("<KeyRelease>", self.set_model_cGlu)
        self.ctl_sbx_cGlu.grid(row=2, column=1)

        ttk.Label(fr_extra_entry, text="ctAlb, g/L").grid(row=3, column=0)
        self.ctl_sbx_ctAlb = SpinboxFloat(
            fr_extra_entry,
            width=4,
            from_=0,
            to=150,
            format="%.0f",
            increment=1,
            command=self.set_model_ctAlb,
        )
        CreateToolTip(
            self.ctl_sbx_ctAlb,
            "Enter if anion gap is surprisingly low. Hypoalbuminemia causes low AG in starved humans.",
        )
        self.ctl_sbx_ctAlb.bind("<KeyRelease>", self.set_model_ctAlb)
        self.ctl_sbx_ctAlb.grid(row=3, column=1)

        ttk.Label(fr_extra_entry, text="cCrea, μmol/L").grid(row=4, column=0)
        self.ctl_sbx_cCrea = SpinboxFloat(
            fr_extra_entry,
            width=4,
            from_=0.0,
            to=2000.0,
            format="%.0f",
            increment=1,
            command=self.set_model_cCrea,
        )
        self.ctl_sbx_cCrea.bind("<KeyRelease>", self.set_model_cCrea)
        self.ctl_sbx_cCrea.grid(row=4, column=1)
        CreateToolTip(self.ctl_sbx_cCrea, "Serum creatinine (IDMS-calibrated)")

        ttk.Label(fr_extra_entry, text="ctBil, μmol/L").grid(row=5, column=0)
        self.ctl_sbx_ctBil = SpinboxFloat(
            fr_extra_entry,
            width=4,
            from_=0.0,
            to=1000.0,
            format="%.0f",
            increment=1,
            command=self.set_model_ctBil,
        )
        self.ctl_sbx_ctBil.bind("<KeyRelease>", self.set_model_ctBil)
        self.ctl_sbx_ctBil.grid(row=5, column=1)
        CreateToolTip(self.ctl_sbx_ctBil, "Serum bilirubin")

        # TRANSFUSION
        fr_trans_entry = ttk.LabelFrame(fr_entry, text="Transfusion")
        fr_trans_entry.pack(side=tk.LEFT, anchor=tk.N, expand=True, fill=tk.BOTH)

        ctl_btn_trans = ttk.Button(
            fr_trans_entry, text="Reset", command=self.set_input_trans_defaults
        )
        CreateToolTip(fr_trans_entry, "Estimate hemotransfusion therapy needs")
        ctl_btn_trans.grid(row=1, column=0)

        ttk.Label(fr_trans_entry, text="ctHb, g/L").grid(row=2, column=0)
        self.ctl_sbx_ctHb = SpinboxFloat(
            fr_trans_entry,
            width=4,
            from_=0,
            to=500,
            format="%.0f",
            increment=1,
            command=self.set_model_ctHb,
        )
        CreateToolTip(
            self.ctl_sbx_ctHb,
            "PRBC dosage for anemia. Free water deficit by Hct if too high.",
        )
        self.ctl_sbx_ctHb.bind("<KeyRelease>", self.set_model_ctHb)
        self.ctl_sbx_ctHb.grid(row=2, column=1)

        ttk.Label(fr_trans_entry, text="PLT, 10⁹/L").grid(row=3, column=0)
        self.ctl_sbx_plt = SpinboxFloat(
            fr_trans_entry,
            width=4,
            from_=0,
            to=3000,
            format="%.0f",
            increment=1,
            command=self.set_model_plt,
        )
        CreateToolTip(
            self.ctl_sbx_plt,
            "Low count provokes spontaneous bleeding. Overall count promotes clot density",
        )
        self.ctl_sbx_plt.bind("<KeyRelease>", self.set_model_plt)
        self.ctl_sbx_plt.grid(row=3, column=1)

        ttk.Label(fr_trans_entry, text="Fib, g/L").grid(row=4, column=0)
        self.ctl_sbx_fib = SpinboxFloat(
            fr_trans_entry,
            width=4,
            from_=0,
            to=50,
            format="%.1f",
            increment=0.1,
            command=self.set_model_fib,
        )
        CreateToolTip(
            self.ctl_sbx_fib,
            "Clot density. Consumed during bleeding. Amount is reduced in liver impairment.",
        )
        self.ctl_sbx_fib.bind("<KeyRelease>", self.set_model_fib)
        self.ctl_sbx_fib.grid(row=4, column=1)

        ttk.Label(fr_trans_entry, text="INR").grid(row=5, column=0)
        self.ctl_sbx_inr = SpinboxFloat(
            fr_trans_entry,
            width=4,
            from_=0,
            to=50,
            format="%.2f",
            increment=0.01,
            command=self.set_model_inr,
        )
        CreateToolTip(
            self.ctl_sbx_inr,
            "Created for warfarin monitoring. High if overall coagulation factors or liver function are impaired.",
        )
        self.ctl_sbx_inr.bind("<KeyRelease>", self.set_model_inr)
        self.ctl_sbx_inr.grid(row=5, column=1)

        # Text view
        self.TxtView = TextHtmlView(self)
        self.TxtView.pack(expand=True, fill=tk.BOTH)
        self.set_input_abg_defaults()
        self.set_input_elec_defaults()
        self.set_input_extra_defaults()
        self.set_input_trans_defaults()
        self.TxtView.set_text(
            textwrap.dedent(
                """\
            Make sure you set sex, body weight.

            Use real patient's data: all electrolytes interconnected by electroneutrality law, Henderson-Hasselbalch equation. So even if you enter values in reference range, calculations can produce a broken result, especially anion gap.

            Same applies for analytical errors in lab: garbage in - garbage out. Some imagined book case studies will fail too.
            """
            )
        )
        # This one is quite good: https://web.archive.org/web/20170829095349/http://fitsweb.uchc.edu/student/selectives/TimurGraham/Cases.html

    def set_input_abg_defaults(self, event=None):
        self.ctl_sbx_pH.delete(0, tk.END)
        self.ctl_sbx_pH.insert(0, f"{abg.norm_pH_mean:.2f}")
        self.set_model_pH()
        self.ctl_sbx_pCO2.delete(0, tk.END)
        self.ctl_sbx_pCO2.insert(0, f"{abg.norm_pCO2mmHg_mean:.0f}")
        self.set_model_pCO2()

    def set_input_elec_defaults(self, event=None):
        self.ctl_sbx_K.delete(0, tk.END)
        self.ctl_sbx_K.insert(0, f"{abg.norm_K_mean:.1f}")
        self.set_model_K()
        self.ctl_sbx_Na.delete(0, tk.END)
        self.ctl_sbx_Na.insert(0, f"{abg.norm_Na_mean:.0f}")
        self.set_model_Na()
        self.ctl_sbx_Cl.delete(0, tk.END)
        self.ctl_sbx_Cl.insert(0, f"{abg.norm_Cl_mean:.0f}")
        self.set_model_Cl()

    def set_input_extra_defaults(self, event=None):
        self.ctl_sbx_cGlu.delete(0, tk.END)
        self.ctl_sbx_cGlu.insert(0, str(abg.norm_cGlu_mean))
        self.set_model_cGlu()
        self.ctl_sbx_ctAlb.delete(0, tk.END)
        self.ctl_sbx_ctAlb.insert(0, f"{abg.norm_ctAlb_mean:.0f}")
        self.set_model_ctAlb()
        self.ctl_sbx_cCrea.delete(0, tk.END)
        self.ctl_sbx_cCrea.insert(0, f"{abg.norm_cCrea:.0f}")
        self.set_model_cCrea()
        self.ctl_sbx_ctBil.delete(0, tk.END)
        self.ctl_sbx_ctBil.insert(0, f"{abg.norm_ctBil:.0f}")
        self.set_model_ctBil()

    def set_input_trans_defaults(self, event=None):
        self.ctl_sbx_ctHb.delete(0, tk.END)
        self.ctl_sbx_ctHb.insert(
            0, f"{abg.norm_hb_mean:.0f}"
        )  # g/L, mean value for both sexes
        self.set_model_ctHb()
        self.ctl_sbx_plt.delete(0, tk.END)
        self.ctl_sbx_plt.insert(0, f"{abg.norm_plt_mean:.0f}")
        self.set_model_plt()
        self.ctl_sbx_fib.delete(0, tk.END)
        self.ctl_sbx_fib.insert(0, f"{abg.norm_fib_mean:.1f}")
        self.set_model_fib()
        self.ctl_sbx_inr.delete(0, tk.END)
        self.ctl_sbx_inr.insert(0, f"{abg.norm_inr_mean:.2f}")
        self.set_model_inr()

    def set_model_pH(self, event=None):
        self.human.blood_abg_pH = float(self.ctl_sbx_pH.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_pCO2(self, event=None):
        self.human.blood_abg_pCO2 = float(self.ctl_sbx_pCO2.get()) * abg.kPa
        self.event_generate("<<HumanModelChanged>>")

    def set_model_K(self, event=None):
        self.human.blood_abg_cK = float(self.ctl_sbx_K.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_Na(self, event=None):
        self.human.blood_abg_cNa = float(self.ctl_sbx_Na.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_Cl(self, event=None):
        self.human.blood_abg_cCl = float(self.ctl_sbx_Cl.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_ctAlb(self, event=None):
        self.human.blood_abg_ctAlb = float(self.ctl_sbx_ctAlb.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_cGlu(self, event=None):
        self.human.blood_abg_cGlu = float(self.ctl_sbx_cGlu.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_cCrea(self, event=None):
        self.human.blood_abg_cCrea = float(self.ctl_sbx_cCrea.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_ctBil(self, event=None):
        self.human.blood_bchem_ctBil = float(self.ctl_sbx_ctBil.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_ctHb(self, event=None):
        self.human.blood_cbc_hb = float(self.ctl_sbx_ctHb.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_plt(self, event=None):
        self.human.blood_cbc_plt = float(self.ctl_sbx_plt.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_fib(self, event=None):
        self.human.blood_coag_fib = float(self.ctl_sbx_fib.get())
        self.event_generate("<<HumanModelChanged>>")

    def set_model_inr(self, event=None):
        self.human.blood_coag_inr = float(self.ctl_sbx_inr.get())
        self.event_generate("<<HumanModelChanged>>")

    def eval(self, event=None):
        self.lbl_hco3["text"] = f"{self.human.blood_abg_hco3p:.1f}"
        self.human.init()
        self.TxtView.set_text(self.human.flags.render() + self.human.eval_labs())


class CreateToolTip:
    """Create a tooltip for a given widget."""

    def __init__(self, parent, text="", delay=500, wraplength=180):
        self.parent = parent
        self.delay = delay  # milliseconds
        self.wraplength = wraplength  # pixels
        self.text = text
        self.parent.bind("<Enter>", self.enter, add="+")
        self.parent.bind("<Leave>", self.leave, add="+")
        self.parent.bind("<ButtonPress>", self.leave)
        self.id = None
        self.tw = None

    def enter(self, event=None):
        self.schedule()

    def leave(self, event=None):
        self.unschedule()
        self.hidetip()

    def schedule(self):
        self.unschedule()
        self.id = self.parent.after(self.delay, self.showtip)

    def unschedule(self):
        _id, self.id = self.id, None
        if _id:
            self.parent.after_cancel(_id)

    def hidetip(self):
        tw, self.tw = self.tw, None
        if tw:
            tw.destroy()

    def showtip(self, event=None):
        x, y, _cx, _cy = self.parent.bbox(tk.INSERT)
        x += self.parent.winfo_rootx() + 25
        y += self.parent.winfo_rooty() + 20
        # Creates a toplevel window
        self.tw = tk.Toplevel(self.parent)
        # Leaves only the label and removes the app window
        self.tw.wm_overrideredirect(True)
        self.tw.wm_geometry(f"+{x:d}+{y:d}")
        label = ttk.Label(
            self.tw,
            text=self.text,
            justify=tk.LEFT,
            background="#ffffff",
            relief="solid",
            borderwidth=1,
            wraplength=self.wraplength,
        )
        label.pack(ipadx=1)


class MenuTooltip(tk.Menu):
    def __init__(self, parent, *args, **kwargs):
        """Menu bar tooltip.

        Args:
            parent: 'root' or 'Menubar'
            args: args
            kwargs: kwargs

        https://stackoverflow.com/questions/3929355/making-menu-options-with-checkbutton-in-tkinter
        https://stackoverflow.com/questions/55316791/how-can-i-add-a-tooltip-to-menu-item
        """
        super().__init__(parent, *args, **kwargs)
        self.parent = parent
        self.tooltip = list()
        self.tooltip_active = None

        self.waittime = 800  # milliseconds
        self.wraplength = 180  # pixels
        self.id = None
        self.tw = None

        # https://stackoverflow.com/questions/4220441/python-tkinter-bind-to-event-related-to-currently-selected-menu-item
        # self.bind('<<MenuSelect>>', self.leave)
        self.bind("<Motion>", self.schedule)
        self.bind("<ButtonPress>", self.leave)
        self.parent.bind("<Leave>", self.leave)
        self.parent.bind("<FocusOut>", self.leave)

    def add_command(self, *cnf, **kwargs):
        """Wrap function."""
        tooltip = kwargs.get("tooltip")
        if tooltip:
            del kwargs["tooltip"]
        super().add_command(*cnf, **kwargs)
        self.add_tooltip(len(self.tooltip), tooltip)

    def add_checkbutton(self, *cnf, **kwargs):
        """Wrap function."""
        tooltip = kwargs.get("tooltip")
        if tooltip:
            del kwargs["tooltip"]
        super().add_checkbutton(*cnf, **kwargs)
        self.add_tooltip(len(self.tooltip), tooltip)

    def add_tooltip(self, index: int, tooltip=None) -> None:
        """Add menu tooltip.

        Args:
            index: Index (0-based) of the Menu Item
            tooltip: Text to show as Tooltip
        """
        self.tooltip.append((self.yposition(index) + 2, tooltip))

    def schedule(self, event):
        self.unschedule()
        self.id = self.parent.after(self.waittime, self.show_tooltip, event)

    def show_tooltip(self, event):
        """Loop .tooltip to find matching Menu Item."""
        for idx in range(len(self.tooltip) - 1, -1, -1):
            if event.y >= self.tooltip[idx][0]:
                # Show tooltip
                self.leave()
                if self.tooltip[idx][1]:  # Has tooltip text
                    self.tooltip_active = idx
                    x = self.winfo_pointerx() + 10
                    y = self.winfo_pointery()
                    self.tw = tk.Toplevel(self)
                    # Leaves only the label and removes the app window
                    self.tw.wm_overrideredirect(True)
                    self.tw.wm_geometry(f"+{x:d}+{y:d}")
                    label = ttk.Label(
                        self.tw,
                        text=self.tooltip[idx][1],
                        justify=tk.LEFT,
                        background="#ffffff",
                        relief=tk.SOLID,
                        borderwidth=1,
                        wraplength=self.wraplength,
                    )
                    label.pack(ipadx=1)
                return

    def leave(self, event=None):
        self.unschedule()
        if self.tooltip_active is not None:
            self.hidetip()
            self.tooltip_active = None

    def hidetip(self):
        tw, self.tw = self.tw, None
        if tw:
            tw.destroy()

    def unschedule(self):
        _id, self.id = self.id, None
        if _id:
            self.parent.after_cancel(_id)


def visit_website(event=None):
    import webbrowser

    webbrowser.open_new_tab(heval.__url__)


def magic8ball() -> str:
    """Well-known superior mind popularized by the movie "Interstate 60".

    Provides answers for any yes/no question.

    References:
        * https://en.wikipedia.org/wiki/Magic_8-Ball
        * https://en.wikipedia.org/wiki/Interstate_60
    """
    answers = (
        "It is certain",
        "It is decidedly so",
        "Without a doubt",
        "Yes definitely",
        "You may rely on it",
        "As I see it, yes",
        "Most likely",
        "Outlook good",
        "Yes",
        "Signs point to yes",
        "Reply hazy, try again",
        "Ask again later",
        "Better not tell you now",
        "Cannot predict now",
        "Concentrate and ask again",
        "Don't count on it",
        "My reply is no",
        "My sources say no",
        "Outlook not so good",
        "Very doubtful",
    )
    return random.choice(answers)


def main():
    root = tk.Tk()
    MainWindow(root).pack(expand=True, fill=tk.BOTH)
    root.mainloop()


if __name__ == "__main__":
    main()
