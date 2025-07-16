import re
import os
import pandas as pd
import matplotlib.pyplot as plt
from itertools import combinations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.dates import DateFormatter
import matplotlib.dates as mdates

# Apply global grayscale style
plt.style.use('grayscale')

APP_TITLE = "Aether Quant | Trade Performance Suite"

# Custom priority for sorting confluences by timeframe
TIMEFRAME_PRIORITY = {
    '1M': 1, '2M': 2, '3M': 3, '5M': 4, '15M': 5, '30M': 6,
    '1H': 7, '2H': 8, '4H': 9, 'D': 10, 'W': 11, 'M': 12
}


def parse_rr(rr_str):
    if pd.isna(rr_str):
        return None
    rr_str = str(rr_str).strip()
    if ':' in rr_str:
        parts = rr_str.split(':')
        try:
            return float(parts[1]) / float(parts[0])
        except:
            return None
    else:
        try:
            return float(rr_str)
        except:
            return None

def load_csv():
    file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
    if file_path:
        df = pd.read_csv(file_path)
        app.load_data(df, os.path.basename(os.path.dirname(file_path)))

class TradeAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.df = None
        self.folder_name = ""
        self.pair_stats_df = pd.DataFrame()
        self.show_only_profitable = False

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        self.create_menu()
        self.create_equity_tab()
        self.create_confluence_tab()
        self.create_pair_tab()

    def extract_timeframe(self, confluence):
        confluence = confluence.upper()
        for tf in ["1M", "5M", "15M", "30M", "1H", "4H"]:
            if tf in confluence:
                return tf
        return "Other"

    def create_menu(self):
        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label="Load CSV", command=load_csv)
        filemenu.add_separator()
        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)
        self.root.config(menu=menubar)

    def create_equity_tab(self):
        self.tab1 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab1, text='Equity Curve')
        self.fig1, (self.ax1, self.ax_month) = plt.subplots(2, 1, figsize=(10, 8))
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.tab1)
        self.canvas1.get_tk_widget().pack(fill='both', expand=True)

    def create_confluence_tab(self):
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text='Win Rate by Confluence')
        self.fig2, self.ax2 = plt.subplots(figsize=(10, 5))
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab2)
        self.canvas2.get_tk_widget().pack(fill='both', expand=True)

        self.slider_frame = ttk.Frame(self.tab2)
        self.slider_frame.pack()
        ttk.Label(self.slider_frame, text="Min Trades:").pack(side='left')
        self.slider = tk.Scale(self.slider_frame, from_=1, to=10, orient='horizontal', command=self.plot_confluences)
        self.slider.set(3)
        self.slider.pack(side='left')

    def create_pair_tab(self):
        self.tab3 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab3, text='Confluence Pair Stats')
        self.table = tk.Text(self.tab3, wrap='none', bg='white', fg='black')
        self.table.pack(fill='both', expand=True)

        self.pair_min_trades = tk.IntVar(value=1)
        self.trade_slider = tk.Scale(self.tab3, from_=1, to=20, orient='horizontal',
                                     label='Min Trades per Pair', variable=self.pair_min_trades,
                                     command=lambda x: self.analyze_pairs(),
                                     bg='white', fg='black')

        self.trade_slider.pack(pady=5)

        # Timeframe filter dropdown
        self.selected_tf = tk.StringVar(value="All")
        ttk.Label(self.tab3, text="Filter by Timeframe:").pack()
        ttk.OptionMenu(self.tab3, self.selected_tf, "All", "1M", "5M", "15M", "30M", "1H", "4H",
                       command=lambda _: self.analyze_pairs()).pack()

        btn_frame = ttk.Frame(self.tab3)
        btn_frame.pack()
        tk.Button(btn_frame, text="Save Stats to CSV", command=self.save_stats).pack(side='left', padx=5)
        tk.Button(btn_frame, text="Toggle Profitable Only", command=self.toggle_profitable).pack(side='left', padx=5)

    def load_data(self, df, folder_name):
        self.df = df
        self.folder_name = folder_name
        self.analyze_equity()
        self.plot_confluences()
        self.analyze_pairs()

    def analyze_equity(self):
        df = self.df.copy()
        df['P&L'] = df['P&L'].replace('[\$,]', '', regex=True).astype(float)
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.sort_values('Date')
        df['Equity'] = df['P&L'].cumsum()

        self.ax1.clear()
        self.ax1.plot(df['Date'], df['Equity'], marker='o', linewidth=2, color='black')
        self.ax1.set_title(f"Equity Curve - {self.folder_name}")
        self.ax1.set_xlabel("Date")
        self.ax1.set_ylabel("Cumulative P&L")
        self.ax1.grid(True)

        self.ax_month.clear()
        monthly = df.groupby(df['Date'].dt.to_period('M'))['P&L'].sum().reset_index()
        monthly['Date'] = monthly['Date'].dt.to_timestamp()
        self.ax_month.bar(monthly['Date'].dt.strftime('%b %Y'), monthly['P&L'], color='gray')
        self.ax_month.set_title("Monthly P&L")
        self.ax_month.set_ylabel("P&L")
        self.ax_month.set_xlabel("Month")
        self.ax_month.tick_params(axis='x', rotation=45)
        self.ax_month.grid(True)

        self.canvas1.draw()

    def plot_confluences(self, *_):
        df = self.df.copy()
        df['Trade Outcome'] = df['Trade Outcome'].str.strip().str.title()
        df['Entry Confirmation'] = df['Entry Confirmation'].fillna('').astype(str)
        filtered = df[df['Trade Outcome'].isin(['Win', 'Loss'])]
        min_trades = self.slider.get()

        confluence_stats = {}
        for _, row in filtered.iterrows():
            outcome = row['Trade Outcome']
            confluences = [c.strip() for c in row['Entry Confirmation'].split(',') if c.strip()]
            for c in confluences:
                if c not in confluence_stats:
                    confluence_stats[c] = {'Win': 0, 'Loss': 0}
                confluence_stats[c][outcome] += 1

        stats = []
        for conf, counts in confluence_stats.items():
            total = counts['Win'] + counts['Loss']
            if total >= min_trades:
                win_rate = (counts['Win'] / total) * 100
                stats.append((conf, counts['Win'], counts['Loss'], win_rate))

        def get_timeframe_priority(name):
            for tf, prio in TIMEFRAME_PRIORITY.items():
                if name.upper().startswith(tf):
                    return prio
            return 99

        stats.sort(key=lambda x: (get_timeframe_priority(x[0]), x[3]), reverse=False)

        self.ax2.clear()
        labels = [s[0] for s in stats]
        win_counts = [s[1] for s in stats]
        loss_counts = [s[2] for s in stats]

        self.ax2.barh(labels, win_counts, color='black', label='Wins')
        self.ax2.barh(labels, loss_counts, left=win_counts, color='lightgray', label='Losses')
        self.ax2.set_xlabel("Number of Trades")
        self.ax2.set_title("Win Rate by Confluence")
        self.ax2.legend()
        self.ax2.grid(True)
        self.canvas2.draw()

    def analyze_pairs(self):
        df = self.df.copy()
        df['Trade Outcome'] = df['Trade Outcome'].str.strip().str.title()
        df['Entry Confirmation'] = df['Entry Confirmation'].fillna('').astype(str)
        df['P&L'] = df['P&L'].replace('[\$,]', '', regex=True).astype(float)
        df['RR Ratio'] = df['RR Ratio'].apply(parse_rr)

        filtered = df[df['Trade Outcome'].isin(['Win', 'Loss'])]
        min_trades = self.pair_min_trades.get()
        tf_filter = self.selected_tf.get().strip().upper()

        pair_stats = {}

        for _, row in filtered.iterrows():
            confluences = [c.strip() for c in row['Entry Confirmation'].split(',') if c.strip()]
            rr = row['RR Ratio']
            pnl = row['P&L']
            outcome = row['Trade Outcome']

            for combo in combinations(sorted(confluences), 2):
                pair_a = combo[0].upper()
                pair_b = combo[1].upper()

                if tf_filter != "ALL":
                    tf_regex = r'\b' + re.escape(tf_filter) + r'\b'
                    if not (re.search(tf_regex, pair_a) or re.search(tf_regex, pair_b)):
                        continue

                if combo not in pair_stats:
                    pair_stats[combo] = {'Wins': 0, 'Losses': 0, 'P&Ls': [], 'RRs': []}

                pair_stats[combo]['P&Ls'].append(pnl)
                if pd.notna(rr):
                    pair_stats[combo]['RRs'].append(rr)
                if outcome == 'Win':
                    pair_stats[combo]['Wins'] += 1
                else:
                    pair_stats[combo]['Losses'] += 1

        rows = []
        for pair, stats in pair_stats.items():
            total = stats['Wins'] + stats['Losses']
            if total < min_trades:
                continue

            avg_pnl = sum(stats['P&Ls']) / total
            avg_rr = sum(stats['RRs']) / len(stats['RRs']) if stats['RRs'] else None
            win_rate = (stats['Wins'] / total) * 100
            profitable = 'N/A'
            if avg_rr is not None:
                breakeven = 100 / (1 + avg_rr)
                profitable = '✅ Yes' if win_rate > breakeven else '❌ No'

            rows.append({
                'Confluence A': pair[0],
                'Confluence B': pair[1],
                'Trades': total,
                'Win Rate (%)': round(win_rate, 1),
                'Avg P&L': round(avg_pnl, 2),
                'Avg RR': round(avg_rr, 2) if avg_rr is not None else 'N/A',
                'Profitable': profitable
            })

            self.pair_stats_df = pd.DataFrame(rows)
            df_filtered = self.pair_stats_df.copy()

            if self.show_only_profitable:
                df_filtered = df_filtered[df_filtered['Profitable'] == '✅ Yes']

            df_filtered = df_filtered[df_filtered['Trades'] >= min_trades]
            df_filtered = df_filtered.sort_values(by='Avg P&L', ascending=False)

            self.table.delete('1.0', tk.END)
            self.table.insert(tk.END, df_filtered.to_string(index=False))

        # Create DataFrame
        self.pair_stats_df = pd.DataFrame(rows)

        # Filter for profitable only, if toggle is on
        df_filtered = self.pair_stats_df.copy()
        if self.show_only_profitable:
            df_filtered = df_filtered[df_filtered['Profitable'] == '✅ Yes']

        # Sort and display
        df_filtered = df_filtered.sort_values(by='Avg P&L', ascending=False)
        self.table.delete('1.0', tk.END)
        self.table.insert(tk.END, df_filtered.to_string(index=False))

        self.pair_stats_df = pd.DataFrame(rows)
        df_filtered = self.pair_stats_df.copy()

        if self.show_only_profitable:
            df_filtered = df_filtered[df_filtered['Profitable'] == '✅ Yes']

        df_filtered = df_filtered[df_filtered['Trades'] >= min_trades]
        df_filtered = df_filtered.sort_values(by='Avg P&L', ascending=False)

        self.table.delete('1.0', tk.END)
        self.table.insert(tk.END, df_filtered.to_string(index=False))

    def toggle_profitable(self):
        self.show_only_profitable = not self.show_only_profitable
        self.analyze_pairs()

    def save_stats(self):
        if self.pair_stats_df.empty:
            messagebox.showinfo("No Data", "No confluence pair stats to save.")
            return
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if file_path:
            self.pair_stats_df.to_csv(file_path, index=False)
            messagebox.showinfo("Saved", f"Stats saved to {file_path}")

if __name__ == '__main__':
    root = tk.Tk()
    app = TradeAnalyzerApp(root)
    root.mainloop()