from tkinter import *
from tkinter import ttk
from MineField import MineField


class App:
    OPTIONS = {
        "solve_everything": None,
        "use_lucky_choice": None,
        "use_smart_choice": None,
        "clicking_speed"  : None,
    }

    def __init__(self, root):
        mainframe = ttk.Frame(root)

        mainframe.pack(padx=30, pady=30)

        title = ttk.Label(mainframe, text="Rozwiazywacz")
        title.pack()

        ttk.Button(mainframe, text="Działaj!", command=self.run_solver).pack()
        ttk.Button(mainframe, text="Test", command=self.test).pack()

        # initialize variables
        self.OPTIONS["solve_everything"] = IntVar()
        self.OPTIONS["solve_everything_forever"] = IntVar()
        self.OPTIONS["use_lucky_choice"] = IntVar()
        self.OPTIONS["use_smart_choice"] = IntVar()
        self.OPTIONS["click_middle"] = IntVar()
        self.OPTIONS["clicking_speed"] = StringVar()
        b_frame = Frame(mainframe)

        ttk.Checkbutton(b_frame, text="Rozwiąż grę",
                        variable=self.OPTIONS["solve_everything"]).grid(row=0, sticky=W)
        ttk.Checkbutton(b_frame, text="Rozwiązuj do skutku",
                        variable=self.OPTIONS["solve_everything_forever"]).grid(row=1, sticky=W)
        ttk.Checkbutton(b_frame, text="Kliknij w środek na początek",
                        variable=self.OPTIONS["click_middle"]).grid(row=2, sticky=W)
        ttk.Checkbutton(b_frame, text="Użyj mądrego rozwiązywania",
                        variable=self.OPTIONS["use_smart_choice"]).grid(row=3, sticky=W)
        ttk.Checkbutton(b_frame, text="Umożliwij zgadywanie",
                        variable=self.OPTIONS["use_lucky_choice"]).grid(row=4, sticky=W)

        ttk.Label(b_frame, text="Przerwa pomiędzy\nkliknięciami (s):").grid(row=5, column=0)
        entry = Entry(b_frame,
                      textvariable=self.OPTIONS["clicking_speed"])
        self.OPTIONS["clicking_speed"].set(0.0)
        entry.config(width=4)
        entry.grid(row=5, column=1)

        b_frame.pack()

    def test(self):
        x = self.run_solver()
        x.test()

    def run_solver(self):
        print("Running solver")
        mine_field = MineField()

        mine_field.OPTIONS["solve_everything"] = self.OPTIONS["solve_everything"].get()
        mine_field.OPTIONS["use_lucky_choice"] = self.OPTIONS["use_lucky_choice"].get()
        mine_field.OPTIONS["use_smart_choice"] = self.OPTIONS["use_smart_choice"].get()
        mine_field.OPTIONS["clicking_speed"] = float(self.OPTIONS["clicking_speed"].get())
        # print(mine_field.OPTIONS)
        while True:
            if self.OPTIONS["click_middle"].get() \
                    and mine_field.OPTIONS["use_lucky_choice"]:
                mine_field.click_middle_field()

            solved = mine_field.solver()
            if solved:
                return mine_field
            if self.OPTIONS["solve_everything_forever"].get():
                mine_field.restart()
            else:
                return mine_field



if __name__ == '__main__':
    root = Tk()
    root.style = ttk.Style()
    root.wm_title("Solver")
    root.tk.call("tk", "scaling", 2)

    app = App(root)
    mainloop()
