import os
import pandas as pd
import matplotlib.pyplot as plt
from itertools import combinations
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Configure dark mode for matplotlib
plt.style.use('dark_background')

# Brand name
APP_TITLE = "Aether Quant | Trade Performance Suite"

# Convert RR string to float
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

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True)

        self.create_menu()
        self.create_equity_tab()
        self.create_confluence_tab()
        self.create_pair_tab()

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
        self.fig1, self.ax1 = plt.subplots(figsize=(10, 5))
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.tab1)
        self.canvas1.get_tk_widget().pack(fill='both', expand=True)

    def create_confluence_tab(self):
        self.tab2 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab2, text='Win Rate by Confluence')
        self.fig2, self.ax2 = plt.subplots(figsize=(10, 5))
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.tab2)
        self.canvas2.get_tk_widget().pack(fill='both', expand=True)

    def create_pair_tab(self):
        self.tab3 = ttk.Frame(self.notebook)
        self.notebook.add(self.tab3, text='Confluence Pair Stats')

        self.table = tk.Text(self.tab3, wrap='none', bg='#1e1e1e', fg='white')
        self.table.pack(fill='both', expand=True)

        self.save_button = tk.Button(self.tab3, text="Save Stats to CSV", command=self.save_stats)
        self.save_button.pack(pady=5)

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

        total_trades = len(df)
        total_pnl = df['P&L'].sum()
        win_rate = (df['P&L'] > 0).sum() / total_trades * 100
        avg_pnl = df['P&L'].mean()

        self.ax1.clear()
        self.ax1.plot(df['Date'], df['Equity'], marker='o', linewidth=2)
        self.ax1.set_title(f"Equity Curve - {self.folder_name}")
        self.ax1.set_xlabel("Date")
        self.ax1.set_ylabel("Cumulative P&L")
        self.ax1.grid(True)

        stats_text = f"Total Trades: {total_trades}\nTotal P&L: ${total_pnl:,.2f}\nWin Rate: {win_rate:.1f}%\nAvg P&L: ${avg_pnl:,.2f}"
        self.ax1.text(1.01, 0.5, stats_text, transform=self.ax1.transAxes, fontsize=10, bbox=dict(facecolor='gray', alpha=0.5))

        self.canvas1.draw()

    def plot_confluences(self):
        df = self.df.copy()
        df['Trade Outcome'] = df['Trade Outcome'].str.strip().str.title()
        df['Entry Confirmation'] = df['Entry Confirmation'].fillna('').astype(str)
        filtered = df[df['Trade Outcome'].isin(['Win', 'Loss'])]

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
            win_rate = (counts['Win'] / total) * 100
            stats.append((conf, counts['Win'], counts['Loss'], win_rate))

        stats = sorted(stats, key=lambda x: x[3], reverse=True)

        self.ax2.clear()
        labels = [s[0] for s in stats]
        win_counts = [s[1] for s in stats]
        loss_counts = [s[2] for s in stats]

        self.ax2.barh(labels, win_counts, color='green', label='Wins')
        self.ax2.barh(labels, loss_counts, left=win_counts, color='red', label='Losses')
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
        pair_stats = {}

        for _, row in filtered.iterrows():
            confluences = [c.strip() for c in row['Entry Confirmation'].split(',') if c.strip()]
            rr = row['RR Ratio']
            pnl = row['P&L']
            outcome = row['Trade Outcome']
            for combo in combinations(sorted(confluences), 2):
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
                'Avg RR': round(avg_rr, 2) if avg_rr else 'N/A',
                'Profitable': profitable
            })

        self.pair_stats_df = pd.DataFrame(rows)
        self.pair_stats_df = self.pair_stats_df.sort_values(by='Avg P&L', ascending=False)

        self.table.delete('1.0', tk.END)
        self.table.insert(tk.END, self.pair_stats_df.to_string(index=False))

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
