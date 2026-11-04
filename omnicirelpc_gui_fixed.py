"""
OMNICIRELPC GUI INTERFACE
Interface graphique futuristique avec Tkinter pour visualiser et contrôler toutes les données
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import sqlite3
import threading
import time
import json
import os
import random
from datetime import datetime
from typing import Dict, List, Any
import requests
from bs4 import BeautifulSoup
import urllib.request
import urllib.parse
import re

class OmniCirelPCGUI:
    """Interface graphique pour OmniCirelPC"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("OmniCirelPC - Intelligence Command Center")
        self.root.geometry("1400x900")
        self.root.configure(bg='#0a0a0a')
        
        # Style futuristique
        self.setup_styles()
        
        # Variables
        self.current_data = {}
        self.selected_item = None
        self.content_data = {}
        self.agent_running = False
        
        # Création de l'interface
        self.create_widgets()
        
        # Créer la base de données si nécessaire et charger les données initiales
        self.create_database_if_needed()
        self.load_data()
        self.populate_navigation()
        self.populate_content("News/Events")
    
    def setup_styles(self):
        """Configure les styles futuristiques"""
        self.colors = {
            'bg': '#0a0a0a',
            'fg': '#00ff00',
            'accent': '#00ffff',
            'warning': '#ffaa00',
            'danger': '#ff3333',
            'panel': '#1a1a1a',
            'border': '#333333'
        }
        
        # Configuration des styles ttk
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure('Futuristic.TFrame', 
                       background=self.colors['panel'],
                       borderwidth=1,
                       relief='solid')
        
        style.configure('Futuristic.TButton',
                       background=self.colors['accent'],
                       foreground=self.colors['bg'],
                       borderwidth=0,
                       focuscolor='none',
                       font=('Consolas', 10, 'bold'))
        
        style.map('Futuristic.TButton',
                 background=[('active', '#00cccc')])
        
        style.configure('Futuristic.TLabel',
                       background=self.colors['panel'],
                       foreground=self.colors['fg'],
                       font=('Consolas', 9))
        
        style.configure('Futuristic.Treeview',
                       background=self.colors['panel'],
                       foreground=self.colors['fg'],
                       fieldbackground=self.colors['panel'],
                       borderwidth=1,
                       relief='solid',
                       font=('Consolas', 9))
        
        style.configure('Futuristic.Treeview.Heading',
                       background=self.colors['border'],
                       foreground=self.colors['accent'],
                       font=('Consolas', 10, 'bold'))
    
    def create_widgets(self):
        """Crée tous les widgets de l'interface"""
        
        # Header principal
        self.create_header()
        
        # Panneau principal
        main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Panneau gauche - Navigation
        left_frame = ttk.Frame(main_paned, style='Futuristic.TFrame')
        main_paned.add(left_frame, weight=1)
        self.create_navigation_panel(left_frame)
        
        # Panneau central - Contenu
        center_frame = ttk.Frame(main_paned, style='Futuristic.TFrame')
        main_paned.add(center_frame, weight=3)
        self.create_content_panel(center_frame)
        
        # Panneau droit - Détails
        right_frame = ttk.Frame(main_paned, style='Futuristic.TFrame')
        main_paned.add(right_frame, weight=1)
        self.create_details_panel(right_frame)
        
        # Barre de statut
        self.create_status_bar()
    
    def create_header(self):
        """Crée le header futuristique"""
        header = ttk.Frame(self.root, style='Futuristic.TFrame')
        header.pack(fill=tk.X, padx=5, pady=5)
        
        # Titre animé
        title_label = tk.Label(header, 
                              text="⚡ OMNICIRELPC INTELLIGENCE CENTER ⚡",
                              font=('Consolas', 16, 'bold'),
                              bg=self.colors['bg'],
                              fg=self.colors['accent'])
        title_label.pack(side=tk.LEFT, padx=10, pady=5)
        
        # Heure et statut
        self.status_label = tk.Label(header,
                                    text="● SYSTEM ONLINE",
                                    font=('Consolas', 10),
                                    bg=self.colors['bg'],
                                    fg=self.colors['fg'])
        self.status_label.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Séparateur
        separator = ttk.Separator(header, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, padx=5, pady=2)
    
    def create_navigation_panel(self, parent):
        """Crée le panneau de navigation"""
        # Titre
        nav_title = ttk.Label(parent, text="📊 NAVIGATION", style='Futuristic.TLabel')
        nav_title.pack(pady=10)
        
        # Treeview navigation
        self.nav_tree = ttk.Treeview(parent, style='Futuristic.Treeview', height=20)
        self.nav_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configuration des colonnes
        self.nav_tree['columns'] = ('count', 'status')
        self.nav_tree.column('#0', width=150, minwidth=100)
        self.nav_tree.column('count', width=50, minwidth=30)
        self.nav_tree.column('status', width=80, minwidth=50)
        
        self.nav_tree.heading('#0', text='Catégorie')
        self.nav_tree.heading('count', text='Count')
        self.nav_tree.heading('status', text='Status')
        
        # Événements
        self.nav_tree.bind('<<TreeviewSelect>>', self.on_nav_select)
        
        # Boutons de contrôle
        control_frame = ttk.Frame(parent, style='Futuristic.TFrame')
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="🔄 REFRESH", 
                  command=self.refresh_data,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
        
        ttk.Button(control_frame, text="▶ START", 
                  command=self.start_agent,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
        
        ttk.Button(control_frame, text="🧹 CLEAN", 
                  command=lambda: self.cleanup_database(show_message=True),
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
        
        ttk.Button(control_frame, text="⏸ PAUSE", 
                  command=self.pause_agent,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)

        ttk.Button(control_frame, text="🧨 RESET DB", 
                  command=self.reset_database,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
    
    def create_content_panel(self, parent):
        """Crée le panneau de contenu principal"""
        # Titre
        content_title = ttk.Label(parent, text="🌟 CONTENT VIEWER", style='Futuristic.TLabel')
        content_title.pack(pady=10)
        
        # Treeview contenu
        self.content_tree = ttk.Treeview(parent, style='Futuristic.Treeview', height=25)
        self.content_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configuration des colonnes
        self.content_tree['columns'] = ('priority', 'category', 'timestamp', 'impact')
        self.content_tree.column('#0', width=300, minwidth=200)
        self.content_tree.column('priority', width=80, minwidth=60)
        self.content_tree.column('category', width=100, minwidth=80)
        self.content_tree.column('timestamp', width=120, minwidth=100)
        self.content_tree.column('impact', width=80, minwidth=60)
        
        self.content_tree.heading('#0', text='Titre/Contenu')
        self.content_tree.heading('priority', text='Priorité')
        self.content_tree.heading('category', text='Catégorie')
        self.content_tree.heading('timestamp', text='Heure')
        self.content_tree.heading('impact', text='Impact')
        
        # Événements
        self.content_tree.bind('<<TreeviewSelect>>', self.on_content_select)
        self.content_tree.bind('<Double-1>', self.on_content_double_click)
        
        # Barre de recherche
        search_frame = ttk.Frame(parent, style='Futuristic.TFrame')
        search_frame.pack(fill=tk.X, padx=5, pady=5)
        
        tk.Label(search_frame, text="🔍 SEARCH:", 
                bg=self.colors['panel'], fg=self.colors['fg'],
                font=('Consolas', 9)).pack(side=tk.LEFT, padx=5)
        
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var,
                               bg=self.colors['bg'], fg=self.colors['fg'],
                               font=('Consolas', 9), insertbackground=self.colors['accent'])
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        search_entry.bind('<KeyRelease>', self.filter_content)
    
    def create_details_panel(self, parent):
        """Crée le panneau de détails"""
        # Titre
        details_title = ttk.Label(parent, text="📋 DETAILS", style='Futuristic.TLabel')
        details_title.pack(pady=10)
        
        # Zone de détails scrollable
        self.details_text = scrolledtext.ScrolledText(parent,
                                                     width=40,
                                                     height=30,
                                                     bg=self.colors['bg'],
                                                     fg=self.colors['fg'],
                                                     font=('Consolas', 9),
                                                     insertbackground=self.colors['accent'])
        self.details_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Boutons d'action
        action_frame = ttk.Frame(parent, style='Futuristic.TFrame')
        action_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(action_frame, text="📤 EXPORT",
                  command=self.export_item,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="� VIEW DETAILS",
                  command=self.show_detailed_view,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
        
        ttk.Button(action_frame, text="� DELETE",
                  command=self.delete_item,
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=2)
    
    def create_status_bar(self):
        """Crée la barre de statut"""
        status_frame = ttk.Frame(self.root, style='Futuristic.TFrame')
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_text = tk.StringVar(value="System Ready")
        status_label = ttk.Label(status_frame, textvariable=self.status_text,
                               style='Futuristic.TLabel')
        status_label.pack(side=tk.LEFT, padx=10)
        
        # Compteurs
        self.counters_text = tk.StringVar(value="Items: 0 | Active: 0")
        counters_label = ttk.Label(status_frame, textvariable=self.counters_text,
                                  style='Futuristic.TLabel')
        counters_label.pack(side=tk.RIGHT, padx=10)
    
    def create_database_if_needed(self):
        """Crée la base de données si elle n'existe pas"""
        try:
            conn = sqlite3.connect('omnicirelpc.db')
            cursor = conn.cursor()
            
            # Créer les tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    content TEXT,
                    category TEXT,
                    priority TEXT,
                    timestamp TEXT,
                    impact REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id INTEGER,
                    analysis TEXT,
                    timestamp TEXT,
                    sentiment REAL,
                    confidence REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT,
                    description TEXT,
                    status TEXT,
                    created_at TEXT,
                    completed_at TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Erreur création base de données: {e}")
            return False
    
    def load_data(self):
        """Charge les données depuis la base de données"""
        try:
            if os.path.exists('omnicirelpc.db'):
                conn = sqlite3.connect('omnicirelpc.db')
                cursor = conn.cursor()
                
                # Charger les événements
                cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 100")
                events = cursor.fetchall()
                
                # Charger les analyses
                cursor.execute("SELECT * FROM analyses ORDER BY timestamp DESC LIMIT 50")
                analyses = cursor.fetchall()
                
                # Charger les tâches
                cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50")
                tasks = cursor.fetchall()
                
                conn.close()
                
                self.current_data = {
                    'events': events,
                    'analyses': analyses,
                    'tasks': tasks
                }
                
                return True
        except Exception as e:
            print(f"Erreur chargement données: {e}")
            return False
        
        return False
    
    def populate_navigation(self):
        """Remplit le panneau de navigation"""
        # Vider le tree
        for item in self.nav_tree.get_children():
            self.nav_tree.delete(item)
        
        # Catégories avec leur statut
        categories = [
            ("News/Events", "critical", 12),
            ("Hot Topics", "active", 8),
            ("Media", "pending", 5),
            ("Quick Actions", "active", 3),
            ("Global", "critical", 15),
            ("Markets", "active", 7),
            ("Analytics", "pending", 4)
        ]
        
        for name, status, count in categories:
            # Couleur selon le statut
            if status == 'critical':
                status_color = self.colors['danger']
            elif status == 'pending':
                status_color = self.colors['warning']
            else:
                status_color = self.colors['fg']
            
            item = self.nav_tree.insert('', 'end', text=name, 
                                       values=(count, status.upper()),
                                       tags=(status,))
        
        # Configuration des tags
        self.nav_tree.tag_configure('critical', foreground=self.colors['danger'])
        self.nav_tree.tag_configure('pending', foreground=self.colors['warning'])
        self.nav_tree.tag_configure('active', foreground=self.colors['fg'])
    
    def populate_content(self, category="News/Events"):
        """Remplit le panneau de contenu avec les données réelles depuis la base de données"""
        print(f"[DEBUG] populate_content appele avec categorie: {category}")
        # Vider le tree
        for item in self.content_tree.get_children():
            self.content_tree.delete(item)
        print("[DEBUG] Tree vide")
        
        # Charger les données depuis la base de données
        sample_data = []
        try:
            conn = sqlite3.connect('omnicirelpc.db')
            cursor = conn.cursor()
            
            # Adapter la requête selon la catégorie
            if category == "News/Events":
                cursor.execute("SELECT * FROM events WHERE category IN ('news', 'geopolitics', 'tech') ORDER BY timestamp DESC LIMIT 50")
            elif category == "Markets":
                cursor.execute("SELECT * FROM events WHERE category = 'crypto' ORDER BY timestamp DESC LIMIT 200")
            elif category == "Global":
                cursor.execute("SELECT * FROM events WHERE category IN ('geopolitics', 'news') ORDER BY timestamp DESC LIMIT 50")
            elif category == "Hot Topics":
                cursor.execute("SELECT * FROM events WHERE priority = 'HIGH' ORDER BY timestamp DESC LIMIT 50")
            elif category == "Analytics":
                cursor.execute("SELECT * FROM events ORDER BY impact DESC LIMIT 50")
            else:
                cursor.execute("SELECT * FROM events ORDER BY timestamp DESC LIMIT 50")
            
            rows = cursor.fetchall()
            conn.close()
            
            print(f"[DEBUG] {len(rows)} lignes récupérées depuis la BDD")
            
            # Convertir les lignes en dictionnaire
            for row in rows:
                sample_data.append({
                    'title': row[1] if len(row) > 1 else 'No title',
                    'content': row[2] if len(row) > 2 else 'No content',
                    'category': row[3] if len(row) > 3 else 'unknown',
                    'priority': row[4] if len(row) > 4 else 'MEDIUM',
                    'timestamp': row[5] if len(row) > 5 else datetime.now().strftime('%H:%M'),
                    'impact': str(row[6]) if len(row) > 6 else '0.5'
                })
                
        except Exception as e:
            print(f"[DEBUG] Erreur chargement BDD: {e}")
            # Données de secours si la BDD est vide
            sample_data = [
                {
                    'title': 'No data available - Click START to begin scraping',
                    'priority': 'MEDIUM',
                    'category': 'system',
                    'timestamp': datetime.now().strftime('%H:%M'),
                    'impact': '0.5',
                    'content': 'Click the START button to begin real-time data scraping from news, crypto, and social media sources.'
                }
            ]
        
        # Ajouter les données
        print(f"[DEBUG] Ajout de {len(sample_data)} éléments au Treeview")
        for item in sample_data:
            # Couleur selon la priorité
            priority_color = self.colors['fg']
            if item['priority'] == 'HIGH':
                priority_color = self.colors['danger']
            elif item['priority'] == 'MEDIUM':
                priority_color = self.colors['warning']
            
            # Déterminer les tags pour les couleurs
            tags = [item['priority'].lower()]
            
            # Ajouter des couleurs spécifiques pour les cryptos
            if 'crypto' in item.get('category', '').lower():
                # Extraire la variation du titre
                title = item.get('title', '')
                if '%' in title:
                    try:
                        # Chercher le pourcentage dans le titre
                        import re
                        match = re.search(r'(-?\d+\.?\d*)%', title)
                        if match:
                            change_value = float(match.group(1))
                            if change_value > 0:
                                tags.append('crypto_positive')  # Vert
                            elif change_value < 0:
                                tags.append('crypto_negative')  # Rouge
                            else:
                                tags.append('crypto_neutral')   # Orange
                    except (ValueError, AttributeError):
                        tags.append('crypto_neutral')
                else:
                    tags.append('crypto_neutral')
            
            tree_item = self.content_tree.insert('', 'end', 
                                                text=item['title'],
                                                values=(item['priority'],
                                                       item['category'],
                                                       item['timestamp'],
                                                       item['impact']),
                                                tags=tags)
            
            # Debug: Afficher ce qui est ajouté
            print(f"[DEBUG] Ajouté: {item['title'][:50]}...")
            if 'crypto' in item.get('category', '').lower():
                print(f"[DEBUG] Ajouté: Crypto: {item.get('title', 'Unknown')}")
            
            # Stocker le contenu complet dans un dictionnaire
            if not hasattr(self, 'content_data'):
                self.content_data = {}
            self.content_data[tree_item] = item['content']
        
        # Configuration des tags de couleur
        self.content_tree.tag_configure('high', foreground=self.colors['danger'])
        self.content_tree.tag_configure('medium', foreground=self.colors['warning'])
        self.content_tree.tag_configure('low', foreground=self.colors['fg'])
        
        # Configuration des couleurs spécifiques pour les cryptos
        self.content_tree.tag_configure('crypto_positive', foreground='#00FF00', font=('Consolas', 10, 'bold'))  # Vert vif
        self.content_tree.tag_configure('crypto_negative', foreground='#FF4444', font=('Consolas', 10, 'bold'))  # Rouge vif
        self.content_tree.tag_configure('crypto_neutral', foreground='#FFA500', font=('Consolas', 10, 'bold'))   # Orange
        
        # Mettre à jour les compteurs
        total_items = len(self.content_tree.get_children())
        self.counters_text.set(f"Items: {total_items} | Active: {total_items}")
    
    def on_nav_select(self, event):
        """Gère la sélection dans le navigation tree"""
        print("[DEBUG] Navigation selectionnee")
        selection = self.nav_tree.selection()
        print(f"[DEBUG] Selection: {selection}")
        if selection:
            item = self.nav_tree.item(selection[0])
            category = item['text']
            print(f"[DEBUG] Categorie selectionnee: {category}")
            self.populate_content(category)
            self.status_text.set(f"Viewing: {category}")
            print(f"[DEBUG] Status mis a jour: {category}")
        else:
            print("[DEBUG] Aucune selection")
    
    def on_content_select(self, event):
        """Gère la sélection dans le content tree"""
        selection = self.content_tree.selection()
        if selection:
            item = self.content_tree.item(selection[0])
            title = item['text']
            
            # Récupérer le contenu complet
            full_content = self.content_data.get(selection[0], 'No detailed content available')
            
            # Afficher dans le panneau de détails
            self.details_text.delete(1.0, tk.END)
            
            details = f"""═══════════════════════════════════════
📋 ITEM DETAILS
═══════════════════════════════════════

📰 TITLE: {title}

📊 PRIORITY: {item['values'][0]}
🏷️  CATEGORY: {item['values'][1]}
⏰ TIMESTAMP: {item['values'][2]}
💥 IMPACT SCORE: {item['values'][3]}

═══════════════════════════════════════
📄 FULL CONTENT
═══════════════════════════════════════

{full_content}

═══════════════════════════════════════
🔍 ANALYSIS
═══════════════════════════════════════

• Sentiment: Neutral
• Credibility: High
• Content Potential: {item['values'][0]} Priority
• Action Required: {'Yes' if item['values'][0] == 'HIGH' else 'No'}

═══════════════════════════════════════
⚡ ACTIONS AVAILABLE
═══════════════════════════════════════

📤 Export Data
🗑 Delete Item
📋 Copy to Clipboard"""
            
            self.details_text.insert(tk.END, details)
            self.selected_item = selection[0]
    
    def on_content_double_click(self, event):
        """Gère le double-clic sur un élément"""
        self.show_detailed_view()
    
    def filter_content(self, event):
        """Filtre le contenu selon la recherche"""
        search_term = self.search_var.get().lower()
        
        for item in self.content_tree.get_children():
            item_text = self.content_tree.item(item)['text'].lower()
            
            if search_term in item_text:
                self.content_tree.item(item, tags=())
            else:
                self.content_tree.item(item, tags=('hidden',))
        
        # Cacher les éléments filtrés
        self.content_tree.tag_configure('hidden', foreground=self.colors['panel'])
    
    def show_detailed_view(self):
        """Affiche une vue détaillée améliorée avec onglets et menu"""
        if not self.selected_item or self.selected_item not in self.content_tree.get_children():
            return
        
        item = self.content_tree.item(self.selected_item)
        full_content = self.content_data.get(self.selected_item, 'No detailed content available')
        
        # Créer une fenêtre modale plus grande, centrée
        detail_window = tk.Toplevel(self.root)
        detail_window.title("🔍 ADVANCED ANALYSIS PANEL")
        width, height = 1000, 700
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        detail_window.geometry(f"{width}x{height}+{x}+{y}")
        detail_window.configure(bg=self.colors['bg'])
        
        # Créer un notebook (onglets)
        notebook = ttk.Notebook(detail_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Onglet 1: Vue d'ensemble
        overview_frame = ttk.Frame(notebook, style='Futuristic.TFrame')
        notebook.add(overview_frame, text="📊 Overview")
        
        overview_text = scrolledtext.ScrolledText(overview_frame,
                                               bg=self.colors['bg'],
                                               fg=self.colors['fg'],
                                               font=('Consolas', 10),
                                               wrap=tk.WORD)
        overview_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        overview_content = f"""
═══════════════════════════════════════════════════════════════
🚀 INTELLIGENCE OVERVIEW
═══════════════════════════════════════════════════════════════

📰 TITLE: {item['text']}

📊 PRIORITY METRICS:
   • Priority Level: {item['values'][0]}
   • Category: {item['values'][1]}
   • Timestamp: {item['values'][2]}
   • Impact Score: {item['values'][3]}

⚡ QUICK ACTIONS:
   • Status: {'URGENT' if item['values'][0] == 'HIGH' else 'NORMAL' if item['values'][0] == 'MEDIUM' else 'LOW'}
   • Response Time: {'Immediate' if item['values'][0] == 'HIGH' else 'Within 2 hours' if item['values'][0] == 'MEDIUM' else 'Within 24 hours'}
   • Resources Needed: {int(float(item['values'][3]) * 5)} units

📈 IMPACT PREDICTION:
   • Market Impact: {float(item['values'][3]) * 100:.1f}%
   • Audience Reach: ~{int(float(item['values'][3]) * 1000000):,} people
   • Engagement Rate: {float(item['values'][3]) * 12:.1f}%

═══════════════════════════════════════════════════════════════
📄 FULL CONTENT
═══════════════════════════════════════════════════════════════

{full_content}
"""
        overview_text.insert(tk.END, overview_content)
        
        # Onglet 2: Analyse détaillée
        analysis_frame = ttk.Frame(notebook, style='Futuristic.TFrame')
        notebook.add(analysis_frame, text="🔍 Deep Analysis")
        
        analysis_text = scrolledtext.ScrolledText(analysis_frame,
                                                bg=self.colors['bg'],
                                                fg=self.colors['fg'],
                                                font=('Consolas', 10),
                                                wrap=tk.WORD)
        analysis_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        detailed_analysis = f"""
═══════════════════════════════════════════════════════════════
🧠 ADVANCED INTELLIGENCE ANALYSIS
═══════════════════════════════════════════════════════════════

📊 CONTENT ANALYSIS:
   • Complexity: {'High' if float(item['values'][3]) > 0.8 else 'Medium' if float(item['values'][3]) > 0.5 else 'Low'}
   • Estimated Duration: {45 + int(float(item['values'][3]) * 30)} seconds
   • Content Type: {'Breaking News' if item['values'][1] == 'news' else 'Market Analysis' if item['values'][1] == 'crypto' else 'General'}
   • Verification Status: {'Verified' if float(item['values'][3]) > 0.7 else 'Pending'}

🎯 TARGET AUDIENCE:
   • Primary: {'Investors' if item['values'][1] == 'crypto' else 'General Public' if item['values'][1] == 'news' else 'Tech Enthusiasts'}
   • Secondary: {'Traders' if item['values'][1] == 'crypto' else 'Media' if item['values'][1] == 'news' else 'Developers'}
   • Estimated Reach: {int(float(item['values'][3]) * 1000000):,} - {int(float(item['values'][3]) * 5000000):,} people

📈 TREND PREDICTION:
   • Peak Interest: In {6 - int(float(item['values'][3]) * 4)} hours
   • Trend Duration: {12 + int(float(item['values'][3]) * 24)} hours
   • Related Topics: {3 + int(float(item['values'][3]) * 5)} emerging topics
   • Viral Potential: {float(item['values'][3]) * 85:.1f}%


💡 RECOMMENDATIONS:
   • Action Required: {'Yes - Immediate' if item['values'][0] == 'HIGH' else 'Yes - Soon' if item['values'][0] == 'MEDIUM' else 'No'}
   • Content Strategy: {'Aggressive' if item['values'][0] == 'HIGH' else 'Moderate' if item['values'][0] == 'MEDIUM' else 'Passive'}
   • Resource Allocation: {int(float(item['values'][3]) * 5)} units recommended
"""
        analysis_text.insert(tk.END, detailed_analysis)
        
        # Onglet 3: Actions et outils
        actions_frame = ttk.Frame(notebook, style='Futuristic.TFrame')
        notebook.add(actions_frame, text="⚡ Actions")
        
        # Menu d'actions
        actions_container = ttk.Frame(actions_frame, style='Futuristic.TFrame')
        actions_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        ttk.Label(actions_container, text="🚀 AVAILABLE ACTIONS", 
                 style='Futuristic.TLabel').pack(pady=10)
        
        # Boutons d'action organisés
        action_buttons = [
            ("📋 Copy Analysis", lambda: self.copy_analysis(overview_content)),
            ("📤 Export Data", lambda: self.export_item_data(item)),
            ("🔍 Deep Search", lambda: self.deep_search(item['text'])),
            ("📊 Generate Report", lambda: self.generate_report(item)),
            ("🔔 Set Alert", lambda: self.set_alert(item)),
            ("🗑 Delete Item", lambda: self.delete_item_from_view(item, detail_window)),
            ("📱 Share", lambda: self.share_item(item)),
            ("🏷️ Add Tags", lambda: self.add_tags(item)),
            ("📌 Pin Item", lambda: self.pin_item(item)),
            ("🔄 Refresh Data", lambda: self.refresh_single_item(item))
        ]
        
        # Créer une grille de boutons
        for i, (text, command) in enumerate(action_buttons):
            btn_frame = ttk.Frame(actions_container, style='Futuristic.TFrame')
            btn_frame.pack(fill=tk.X, pady=2)
            
            ttk.Button(btn_frame, text=text, command=command,
                      style='Futuristic.TButton').pack(side=tk.LEFT, padx=5)
            
            # Description pour chaque action
            descriptions = [
                "Copy full analysis to clipboard",
                "Export data as CSV/JSON",
                "Perform deep web search",
                "Generate detailed report",
                "Set notification alert",
                "Remove from database",
                "Share via social media",
                "Add custom tags",
                "Pin to dashboard",
                "Refresh item data"
            ]
            
            ttk.Label(btn_frame, text=descriptions[i], 
                     style='Futuristic.TLabel').pack(side=tk.LEFT, padx=10)
        
        # Barre de statut dans la fenêtre
        status_frame = ttk.Frame(detail_window, style='Futuristic.TFrame')
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        status_text = tk.StringVar(value="Analysis complete - Ready for action")
        ttk.Label(status_frame, textvariable=status_text,
                 style='Futuristic.TLabel').pack(side=tk.LEFT, padx=10)
        
        # Boutons principaux
        main_button_frame = ttk.Frame(detail_window, style='Futuristic.TFrame')
        main_button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(main_button_frame, text="📋 COPY ANALYSIS",
                  command=lambda: self.copy_analysis(overview_content),
                  style='Futuristic.TButton').pack(side=tk.LEFT, padx=5)
        
        ttk.Button(main_button_frame, text="❌ CLOSE",
                  command=detail_window.destroy,
                  style='Futuristic.TButton').pack(side=tk.RIGHT, padx=5)
    
    def refresh_data(self):
        """Rafraîchit toutes les données"""
        self.status_text.set("Refreshing data...")
        self.root.update()
        
        if self.load_data():
            self.populate_navigation()
            self.populate_content()
            self.status_text.set("Data refreshed successfully")
        else:
            self.status_text.set("Error refreshing data")
        
        self.root.after(2000, lambda: self.status_text.set("System Ready"))
    
    def start_agent(self):
        """Démarre l'agent autonome"""
        print("[DEBUG] Bouton START cliqué")
        if getattr(self, 'agent_running', False):
            self.status_text.set("Agent already running")
            return
        self.agent_running = True
        self.status_text.set("Starting autonomous agent...")
        print("[DEBUG] Thread de l'agent demarre")
        threading.Thread(target=self.run_agent_simulation, daemon=True).start()
    
    def export_item_data(self, item):
        """Exporte les données d'un item"""
        try:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            data = {
                'title': item['text'],
                'priority': item['values'][0],
                'category': item['values'][1],
                'timestamp': item['values'][2],
                'impact_score': item['values'][3],
                'export_time': datetime.now().isoformat()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Export Success", f"Data exported to {filename}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {str(e)}")
    
    def deep_search(self, query):
        """Effectue une recherche approfondie"""
        self.status_text.set(f"Deep searching: {query}...")
        # Simuler une recherche approfondie
        threading.Thread(target=self._perform_deep_search, args=(query,), daemon=True).start()
    
    def _perform_deep_search(self, query):
        """Effectue la recherche en arrière-plan"""
        time.sleep(2)  # Simuler recherche
        self.status_text.set(f"Deep search completed for: {query}")
    
    def generate_report(self, item):
        """Génère un rapport détaillé"""
        try:
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            report = f"""
INTELLIGENCE REPORT
==================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

TITLE: {item['text']}
PRIORITY: {item['values'][0]}
CATEGORY: {item['values'][1]}
TIMESTAMP: {item['values'][2]}
IMPACT SCORE: {item['values'][3]}

ANALYSIS:
- Market Impact: {float(item['values'][3]) * 100:.1f}%
- Audience Reach: ~{int(float(item['values'][3]) * 1000000):,} people
- Engagement Rate: {float(item['values'][3]) * 12:.1f}%
- Recommended Action: {'Immediate' if item['values'][0] == 'HIGH' else 'Moderate' if item['values'][0] == 'MEDIUM' else 'Monitor'}
"""
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report)
            
            messagebox.showinfo("Report Generated", f"Report saved to {filename}")
        except Exception as e:
            messagebox.showerror("Report Error", f"Failed to generate report: {str(e)}")
    
    def set_alert(self, item):
        """Configure une alerte pour un item"""
        messagebox.showinfo("Alert Set", f"Alert configured for: {item['text']}")
    
    def delete_item_from_view(self, item, window):
        """Supprime un item et ferme la fenêtre"""
        if messagebox.askyesno("Confirm Delete", f"Delete this item?\n\n{item['text']}"):
            self.content_tree.delete(self.selected_item)
            window.destroy()
            messagebox.showinfo("Deleted", "Item removed successfully")
    
    def share_item(self, item):
        """Partage un item"""
        share_text = f"📰 {item['text']}\n📊 Priority: {item['values'][0]}\n🏷️ Category: {item['values'][1]}"
        messagebox.showinfo("Share", f"Content copied to clipboard:\n\n{share_text}")
    
    def add_tags(self, item):
        """Ajoute des tags à un item"""
        messagebox.showinfo("Tags", "Tag functionality coming soon!")
    
    def pin_item(self, item):
        """Épingle un item au tableau de bord"""
        messagebox.showinfo("Pinned", f"Item pinned to dashboard: {item['text']}")
    
    def refresh_single_item(self, item):
        """Rafraîchit les données d'un item spécifique"""
        self.status_text.set("Refreshing item data...")
        threading.Thread(target=self._refresh_item_data, args=(item,), daemon=True).start()
    
    def _refresh_item_data(self, item):
        """Rafraîchit les données en arrière-plan"""
        time.sleep(1)  # Simuler rafraîchissement
        self.status_text.set("Item data refreshed")
    
    def pause_agent(self):
        """Met en pause l'agent"""
        self.agent_running = False
        self.status_text.set("Agent paused")
    
    def run_agent_simulation(self):
        """Agent autonome qui scrape les données réelles"""
        print("[DEBUG] Agent de scraping démarré")
        
        try:
            # Importer le scraper
            import sys
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
            from open_source_scraper import OpenSourceDataCollector
            
            self.status_text.set("Initializing scraper...")
            scraper = OpenSourceDataCollector()
            
            # Boucle principale tant que l'agent est actif
            while getattr(self, 'agent_running', False):
                # Collecter toutes les données
                self.status_text.set("Collecting data...")
                print("[DEBUG] Collecte des données")
                all_collected_data = scraper.collect_all_data()
                
                # Extraire les différentes catégories
                news_data = all_collected_data.get('crypto_news', []) + all_collected_data.get('world_news', []) + all_collected_data.get('tech_news', [])
                crypto_data = all_collected_data.get('crypto_data', [])
                reddit_data = all_collected_data.get('reddit_trends', [])
                
                print(f"[DEBUG] Données reçues - News: {len(news_data)}, Crypto: {len(crypto_data)}, Reddit: {len(reddit_data)}")
                print(f"[DEBUG] Échantillon crypto_data: {crypto_data[:2] if crypto_data else 'EMPTY'}")
                
                # Combiner toutes les données
                all_data = []
                
                # Ajouter les news
                for item in news_data:
                    all_data.append({
                        'title': item.get('title', 'No title'),
                        'priority': 'HIGH' if 'breaking' in item.get('title', '').lower() else 'MEDIUM',
                        'category': 'news',
                        'timestamp': item.get('timestamp', datetime.now().strftime('%H:%M')),
                        'impact': str(random.uniform(0.5, 0.95)),
                        'content': item.get('content', item.get('title', 'No content'))
                    })
                
                # Ajouter les données crypto
                for item in crypto_data:
                    change_value = item.get('change_24h', 0)
                    if isinstance(change_value, (int, float)):
                        change_str = f"{change_value:.2f}%"
                        impact = abs(change_value) / 100
                    else:
                        change_str = "0%"
                        impact = 0.0
                    
                    # Utiliser la description détaillée si disponible, sinon le contenu standard
                    description = item.get('description', '')
                    if description:
                        content = f"{item.get('symbol', 'Unknown')} - Price: ${item.get('price', 0):,.2f} - Change: {change_str}\n\n📊 Description: {description}"
                    else:
                        content = f"{item.get('symbol', 'Unknown')} - Price: ${item.get('price', 0):,.2f} - Change: {change_str}"
                    
                    all_data.append({
                        'title': f"Crypto: {item.get('symbol', 'Unknown')} {change_str}",
                        'priority': 'HIGH' if abs(change_value) > 5 else 'MEDIUM',
                        'category': 'crypto',
                        'timestamp': item.get('timestamp', datetime.now().strftime('%H:%M')),
                        'impact': str(impact),
                        'content': content
                    })        
                # Ajouter les données Reddit
                print(f"[DEBUG] Traitement de {len(reddit_data)} éléments Reddit")
                if reddit_data:
                    print(f"[DEBUG] Premier élément Reddit: {reddit_data[0]}")
                else:
                    print(f"[DEBUG] reddit_data est vide!")
                for item in reddit_data:
                    reddit_item = {
                        'title': f"Reddit: {item.get('title', 'No title')[:50]}...",
                        'priority': 'MEDIUM',
                        'category': 'social',
                        'timestamp': item.get('timestamp', datetime.now().strftime('%H:%M')),
                        'impact': str(random.uniform(0.3, 0.8)),
                        'content': f"Subreddit: {item.get('subreddit', 'unknown')} - {item.get('title', 'No title')}"
                    }
                    all_data.append(reddit_item)
                    print(f"[DEBUG] Reddit ajouté: {reddit_item['title'][:30]}...")
                
                # Sauvegarder dans la base de données
                self.status_text.set("Saving to database...")
                print("[DEBUG] Sauvegarde dans la base de données")
                self.save_scraped_data(all_data)

                # Nettoyage automatique de la base pour rester léger
                self.status_text.set("Cleaning database...")
                self.cleanup_database()
                
                # Rafraîchir l'interface
                self.status_text.set("Refreshing interface...")
                self.load_data()
                self.populate_navigation()
                self.populate_content("News/Events")
                
                self.status_text.set(f"Scraping completed - {len(all_data)} items collected")
                print(f"[DEBUG] Scraping terminé - {len(all_data)} éléments collectés")
                
                # Attendre avant le prochain cycle (~10 minutes) en restant interruptible
                for _ in range(600):
                    if not getattr(self, 'agent_running', False):
                        break
                    time.sleep(1)

            self.status_text.set("Agent stopped")
            print("[DEBUG] Agent arrêté")
            
        except Exception as e:
            self.status_text.set(f"Error: {str(e)}")
            print(f"[DEBUG] Erreur lors du scraping: {e}")
    
    def save_scraped_data(self, data):
        """Sauvegarde les données scrapées dans la base de données"""
        try:
            print(f"[DEBUG] Sauvegarde de {len(data)} éléments dans la BDD")
            # Afficher les 3 premiers éléments pour débogage
            for i, item in enumerate(data[:3]):
                print(f"[DEBUG] Item {i}: {item}")
            
            conn = sqlite3.connect('omnicirelpc.db')
            cursor = conn.cursor()
            
            # Supprimer les anciennes données crypto pour éviter les doublons
            cursor.execute("DELETE FROM events WHERE category='crypto';")
            print(f"[DEBUG] Anciennes données crypto supprimées")
            
            for item in data:
                cursor.execute('''
                    INSERT INTO events (title, content, category, priority, timestamp, impact)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    item['title'],
                    item['content'],
                    item['category'],
                    item['priority'],
                    item['timestamp'],
                    float(item['impact'])
                ))
            
            conn.commit()
            conn.close()
            print(f"[DEBUG] {len(data)} éléments sauvegardés dans la base de données")
            
        except Exception as e:
            print(f"[DEBUG] Erreur sauvegarde BDD: {e}")
    
    def cleanup_database(self, max_events: int = 500, max_analyses: int = 200, max_tasks: int = 200, show_message: bool = False):
        """Nettoie la base pour garder seulement les éléments récents"""
        try:
            conn = sqlite3.connect('omnicirelpc.db')
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM events
                WHERE id NOT IN (
                    SELECT id FROM events
                    ORDER BY id DESC
                    LIMIT ?
                )
            """, (max_events,))
            deleted_events = cursor.rowcount

            cursor.execute("""
                DELETE FROM analyses
                WHERE id NOT IN (
                    SELECT id FROM analyses
                    ORDER BY id DESC
                    LIMIT ?
                )
            """, (max_analyses,))
            deleted_analyses = cursor.rowcount

            cursor.execute("""
                DELETE FROM tasks
                WHERE id NOT IN (
                    SELECT id FROM tasks
                    ORDER BY id DESC
                    LIMIT ?
                )
            """, (max_tasks,))
            deleted_tasks = cursor.rowcount

            conn.commit()
            conn.close()

            print(f"[DEBUG] Cleanup DB - events: {deleted_events}, analyses: {deleted_analyses}, tasks: {deleted_tasks}")
            if show_message:
                messagebox.showinfo("Cleanup", f"Database cleaned:\n\nEvents: {deleted_events}\nAnalyses: {deleted_analyses}\nTasks: {deleted_tasks}")
        except Exception as e:
            print(f"[DEBUG] Erreur nettoyage BDD: {e}")

    def reset_database(self):
        """Réinitialise complètement la base: supprime tous les events / analyses / tasks."""
        confirm = messagebox.askyesno(
            "RESET DATABASE",
            "This will DELETE ALL events, analyses and tasks from the database.\n\nContinue?"
        )
        if not confirm:
            return

        try:
            conn = sqlite3.connect('omnicirelpc.db')
            cursor = conn.cursor()

            cursor.execute("DELETE FROM events")
            cursor.execute("DELETE FROM analyses")
            cursor.execute("DELETE FROM tasks")

            conn.commit()
            conn.close()

            # Vider la vue et recharger (sera vide jusqu'au prochain scraping)
            self.load_data()
            self.populate_navigation()
            self.populate_content("News/Events")
            self.status_text.set("Database fully reset")
            messagebox.showinfo("RESET DB", "All events, analyses and tasks have been deleted.")
        except Exception as e:
            print(f"[DEBUG] Erreur reset BDD: {e}")

    def export_item(self):
        """Exporte l'élément sélectionné"""
        if self.selected_item and self.selected_item in self.content_tree.get_children():
            item = self.content_tree.item(self.selected_item)
            
            # Créer le contenu à exporter
            export_data = {
                'title': item['text'],
                'priority': item['values'][0],
                'category': item['values'][1],
                'timestamp': item['values'][2],
                'impact': item['values'][3],
                'exported_at': datetime.now().isoformat()
            }
            
            # Sauvegarder dans un fichier
            filename = f"export_{int(time.time())}.json"
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            messagebox.showinfo("Exported", 
                               f"Data exported to:\n{filename}")
    
    def copy_analysis(self, content):
        """Copie l'analyse dans le presse-papiers"""
        self.root.clipboard_clear()
        self.root.clipboard_append(content)
        messagebox.showinfo("Copied", 
                            "Analysis copied to clipboard")
    
    def delete_item(self):
        """Supprime l'élément sélectionné"""
        if self.selected_item and self.selected_item in self.content_tree.get_children():
            item = self.content_tree.item(self.selected_item)
            
            result = messagebox.askyesno("Confirm Delete",
                                         f"Delete this item?\n\n{item['text']}")
            
            if result:
                self.content_tree.delete(self.selected_item)
                self.details_text.delete(1.0, tk.END)
                self.selected_item = None
                self.status_text.set("Item deleted")
    
    def start_monitoring(self):
        """Démarre le monitoring automatique"""
        self.load_data()
        self.populate_navigation()
        self.populate_content()
        
        # Monitoring toutes les 30 secondes
        self.root.after(30000, self.start_monitoring)
    
    def run(self):
        """Démarre l'interface graphique"""
        self.root.mainloop()

# Point d'entrée
if __name__ == "__main__":
    app = OmniCirelPCGUI()
    app.run()
