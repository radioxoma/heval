import random
from heval import common

__version__ = "0.1.6"
__url__ = "https://github.com/radioxoma/heval/"
__author__ = "Eugene Dvoretsky"
__doc__ = f"""\
<ul>
    <li>По-умолчанию используется идеальный вес (установлена галочка {common.A.ibw})</li>
    <li>Галочка <dfn>verbose</dfn> включает вывод дополнительной информации</li>
    <li>Аббревиатуры раскрываются по тапу или при наведении курсора</li>
    <li>Спинбоксы прокручиваются колесом мыши</li>
</ul>

<h3>Body</h3>
<p><strong>Введите пол и рост — этого достаточно для большей части антропометрических
расчётов.</strong> Идеальный вес ({common.A.ibw}) рассчитывается по полу и росту автоматически.
Снимите галочку <dfn>Use IBW</dfn> и введите реальный вес, если знаете его.</p>

<p>Мгновенно доступны: {common.A.ibw}, {common.A.bmi}, {common.A.bsa}, объёмы вентиляции, суточная потребность
в питании и жидкости, диурез, доза диализа etc.</p>

<h3>Labs</h3>
<p>Кислотно-щелочной статус оценивается по pH и pCO2. Но в случае
метаболического ацидоза необходимо ввести концентрации K⁺, Na⁺, Cl⁻, чтобы
программа смогла рассчитать анионный промежуток и попыталась найти скрытые
метаболические процессы при помощи Delta ratio.<br>
Пол и вес влияют на рассчитанную инфузионную терапию.</p>
"""

DISCLAIMER = f"""\
<h3>Disclaimer</h3>

<p><blockquote>Heval — экспериментальное программное обеспечение, предназначенное для
использования врачами анестезиологами-реаниматологами. Программа
предоставляется "как есть". Автор не несёт ответственности за ваши
действия и не предоставляет никаких гарантий.</blockquote></p>

<p><blockquote>Heval is an experimental medical software intended for healthcare
specialists. The software is provided "as is". Developer makes no warranties,
express or implied.</blockquote></p>

<p>Heval is a free software and licensed under the terms of
GNU General Public License version 3. Written by {__author__}.
Check source code for references and formulas, contact and support.
<a href="{__url__}" target="_blank">{__url__}</a></p>
""" + "<p>And remember: {}</p>".format(
    random.choice(("It's got what plants crave!", "It's got electrolytes!"))
)
