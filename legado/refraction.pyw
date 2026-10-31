import tkinter as tk
from tkinter import ttk
import math as mt
import numpy as np

# window
window = tk.Tk()
window.title("Optics")
window.geometry("350x400")
window.minsize(350, 400)

# variable
resultado = tk.StringVar()

# function
def ShowResult():
    to_rads = 3.141592653589793 / 180
    to_degrees = 180 / 3.141592653589793
    try:
        # ángulos
        if i_entry.get() == "":
            n1 = float(n1_entry.get())
            n2 = float(n2_entry.get())
            sin_r = np.sin(float(r_entry.get()) * to_rads)
            resultado.set(f"i = {round((mt.asin((sin_r/n1)*n2))*to_degrees,2)}")
        elif r_entry.get() == "":
            n1 = float(n1_entry.get())
            n2 = float(n2_entry.get())
            sin_i = np.sin(float(i_entry.get()) * to_rads)
            resultado.set(f"r = {round((mt.asin((sin_i/n2)*n1))*to_degrees,2)}")
        # índices de refracción
        elif n1_entry.get() == "":
            n2 = float(n2_entry.get())
            sin_i = np.sin(float(i_entry.get()) * to_rads)
            sin_r = np.sin(float(r_entry.get()) * to_rads)
            resultado.set(f"n1 = {round((sin_r/sin_i)*n2,2)}")
        elif n2_entry.get() == "":
            n1 = float(n1_entry.get())
            sin_i = np.sin(float(i_entry.get()) * to_rads)
            sin_r = np.sin(float(r_entry.get()) * to_rads)
            resultado.set(f"n2 = {round((sin_i/sin_r)*n1,2)}")
    except:
        resultado.set(f"Error al ingresar")


# widgets
label1 = ttk.Label(window, text="Óptica", font=("Oswald", 20))

sup_Frame1 = ttk.Frame(window)

n1_frame = ttk.Frame(sup_Frame1)
n1_entry = ttk.Entry(n1_frame, width=10, font=("Oswald", 15))
n1_label = ttk.Label(n1_frame, text="n1:", font=("Oswald", 20))
n1_entry.config(justify="center")

n2_frame = ttk.Frame(sup_Frame1)
n2_entry = ttk.Entry(n2_frame, width=10, font=("Oswald", 15))
n2_label = ttk.Label(n2_frame, text="n2:", font=("Oswald", 20))
n2_entry.config(justify="center")

sup_Frame2 = ttk.Frame(window)

i_frame = ttk.Frame(sup_Frame2)
i_entry = ttk.Entry(i_frame, width=10, font=("Oswald", 15))
i_label = ttk.Label(i_frame, text="I(Ray):", font=("Oswald", 20))
i_entry.config(justify="center")

r_frame = ttk.Frame(sup_Frame2)
r_entry = ttk.Entry(r_frame, width=10, font=("Oswald", 15))
r_label = ttk.Label(r_frame, text="R(Ray):", font=("Oswald", 20))
r_entry.config(justify="center")

result = tk.Label(window, text="", font=("Oswald", 20), textvariable=resultado)

Calc_button = tk.Button(window, text="Calcular", font=("Oswald", 15), command=ShowResult)

# pack
label1.pack(pady=20)

n1_label.pack(side="top", expand=False)
n1_entry.pack(side="top", expand=False, fill="both", padx=20)
n1_frame.pack(side="left", fill="both", expand=True)

n2_label.pack(side="top", expand=False)
n2_entry.pack(side="top", expand=False, fill="both", padx=20)
n2_frame.pack(side="left", fill="both", expand=True)
sup_Frame1.pack(fill="both", expand=True)

i_label.pack(side="top", expand=False)
i_entry.pack(side="top", expand=False, fill="both", padx=20)
i_frame.pack(side="left", fill="both", expand=True)

r_label.pack(side="top", expand=False)
r_entry.pack(side="top", expand=False, fill="both", padx=20)
r_frame.pack(side="left", fill="both", expand=True)
sup_Frame2.pack(fill="both", expand=True)

result.pack()

Calc_button.pack()

window.mainloop()
