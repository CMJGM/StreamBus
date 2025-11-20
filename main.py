"""
StreamBus Photo Downloader - Aplicación Principal con Debug Completo
Descarga automática de fotos de seguridad cada X horas con filtros configurables
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import schedule
import time
import json
import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import re
from collections import defaultdict

# Importar módulos adaptados
from adapted_utils import (
    load_config, save_config, get_config, set_config,
    gps_login, obtener_empresas_disponibles,
    obtener_vehiculos_por_empresa, query_security_photos
)
from adapted_downloader import (
    start_download_job, get_download_job, DownloadJob
)

# Configurar logging
def setup_logging():
    """Configurar sistema de logging"""
    log_dir = get_config('logging.log_directory', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, f"streambus_{datetime.now().strftime('%Y%m%d')}.log")
    
    logging.basicConfig(
        level=getattr(logging, get_config('logging.level', 'INFO')),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class StreamBusDownloader:
    """Aplicación principal de descarga automática"""
    
    def __init__(self):
        # Cargar configuración
        if not load_config():
            self.create_default_config()
            load_config()
        
        setup_logging()
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Iniciando StreamBus Downloader")
        
        # Variables de estado
        self.current_job = None
        self.scheduler_running = False
        self.scheduler_thread = None
        self.empresas_disponibles = []
        self.auto_download_enabled = get_config('automation.enabled', False)
        self.files_tree = None  # Referencia al Treeview de la tabla
        self.files_status_label = None  # Label de estado del análisis
        self.files_summary_label = None  # Label de resumen
        self.refresh_analysis_btn = None  # Botón de refresh
        
        # 🆕 Variables para lógica de scheduler inteligente
        self.last_download_end_time = None
        self.download_in_progress = False
        self.initial_download_done = False
        self.scheduler_paused = False
        
        # Configurar GUI
        ctk.set_appearance_mode(get_config('gui.theme', 'dark'))
        ctk.set_default_color_theme("blue")
        
        self.setup_gui()
        self.load_initial_data()
        
        # Iniciar scheduler si está habilitado
        if self.auto_download_enabled:
            self.start_scheduler()
            
        # 🆕 Ejecutar descarga inicial automática si está habilitada
        if (self.auto_download_enabled and 
            get_config('automation.initial_download_on_startup', True)):
            self.schedule_initial_download()
    
    def create_default_config(self):
        """Crear configuración por defecto si no existe"""
        default_config = {
            "gps": {
                "base_url": "http://190.183.254.253:8088",
                "account": "",
                "password": "",
                "timeout": 30
            },
            "download": {
                "base_directory": os.path.join(os.getcwd(), "downloads", "fotos"),
                "max_workers": 15,
                "concurrent_downloads": 10
            },
            "automation": {
                "enabled": False,
                "interval_hours": 3,
                "start_hour": 6,
                "end_hour": 22,
                "initial_download_on_startup": True,  # 🆕 Descarga inicial al iniciar
                "smart_scheduling": True,  # 🆕 No contar tiempo de descarga en intervalo
                "initial_download_delay_minutes": 2  # 🆕 Delay antes de descarga inicial
            },
            "filters": {
                "default_empresa_id": None,
                "default_hours_back": 6
            },
            "gui": {
                "theme": "dark",
                "window_geometry": "1200x800"
            },
            "logging": {
                "level": "INFO",
                "log_directory": "logs"
            }
        }
        
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    def setup_gui(self):
        """Configurar interfaz gráfica"""
        # Ventana principal
        self.root = ctk.CTk()
        self.root.title(get_config('app.window_title', 'StreamBus Photo Downloader'))
        self.root.geometry(get_config('gui.window_geometry', '1200x800'))
        
        # Configurar grid
        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(0, weight=1)
        
        # Crear sidebar
        self.create_sidebar()
        
        # Crear área principal
        self.create_main_area()
        
        # Crear área de estado
        self.create_status_area()
        
        # Eventos de cierre
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_sidebar(self):
        """Crear panel lateral de navegación"""
        self.sidebar = ctk.CTkFrame(self.root, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar.grid_rowconfigure(4, weight=1)
        
        # Logo/Título
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="🚌 StreamBus\nDownloader", 
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))
        
        # Botones de navegación
        self.nav_buttons = {}
        nav_items = [
            ("🎛️ Configuración", "config"),
            ("📥 Descarga", "download"),
            ("⏰ Automatización", "automation"),
            ("📊 Monitoreo", "monitoring"),
            ("📝 Logs", "logs"),
            ("🔧 Debug", "debug")  # NUEVO PANEL DEBUG
        ]
        
        for i, (text, key) in enumerate(nav_items, 1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                command=lambda k=key: self.show_panel(k),
                height=40
            )
            btn.grid(row=i, column=0, padx=20, pady=10, sticky="ew")
            self.nav_buttons[key] = btn
        
        # Botón de salida
        self.exit_button = ctk.CTkButton(
            self.sidebar,
            text="🚪 Salir",
            command=self.on_closing,
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray80", "gray20"),
            height=40
        )
        self.exit_button.grid(row=10, column=0, padx=20, pady=20, sticky="ew")
    
    def create_main_area(self):
        """Crear área principal con paneles"""
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(0, weight=1)
        
        # Crear todos los paneles
        self.panels = {}
        self.create_config_panel()
        self.create_download_panel()
        self.create_automation_panel()
        self.create_monitoring_panel()
        self.create_logs_panel()
        self.create_debug_panel()  # NUEVO PANEL DEBUG
        
        # Mostrar panel de configuración por defecto
        self.show_panel("config")
    
    def create_config_panel(self):
        """Panel de configuración GPS y directorios"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        self.panels["config"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="⚙️ Configuración", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Configuración GPS
        gps_frame = ctk.CTkFrame(panel)
        gps_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(gps_frame, text="🌐 Configuración GPS", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Usuario
        user_frame = ctk.CTkFrame(gps_frame)
        user_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(user_frame, text="Usuario:").pack(side="left", padx=10)
        self.user_entry = ctk.CTkEntry(user_frame, placeholder_text="Nombre de usuario GPS")
        self.user_entry.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        
        # Contraseña
        pass_frame = ctk.CTkFrame(gps_frame)
        pass_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(pass_frame, text="Contraseña:").pack(side="left", padx=10)
        self.pass_entry = ctk.CTkEntry(pass_frame, placeholder_text="Contraseña GPS", show="*")
        self.pass_entry.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        
        # Servidor
        server_frame = ctk.CTkFrame(gps_frame)
        server_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(server_frame, text="Servidor:").pack(side="left", padx=10)
        self.server_entry = ctk.CTkEntry(server_frame, placeholder_text="http://190.183.254.253:8088")
        self.server_entry.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        
        # Botón probar conexión
        self.test_connection_btn = ctk.CTkButton(
            gps_frame,
            text="🔍 Probar Conexión",
            command=self.test_gps_connection
        )
        self.test_connection_btn.pack(pady=10)
        
        # Configuración de descarga
        download_frame = ctk.CTkFrame(panel)
        download_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(download_frame, text="📁 Configuración de Descarga", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Directorio base
        dir_frame = ctk.CTkFrame(download_frame)
        dir_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(dir_frame, text="Directorio:").pack(side="left", padx=10)
        self.dir_entry = ctk.CTkEntry(dir_frame, placeholder_text="Directorio de descarga")
        self.dir_entry.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        
        self.browse_btn = ctk.CTkButton(
            dir_frame,
            text="📂 Examinar",
            command=self.browse_directory,
            width=100
        )
        self.browse_btn.pack(side="right", padx=10, pady=10)
        
        # Workers
        workers_frame = ctk.CTkFrame(download_frame)
        workers_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(workers_frame, text="Workers paralelos:").pack(side="left", padx=10)
        self.workers_slider = ctk.CTkSlider(workers_frame, from_=1, to=30, number_of_steps=29)
        self.workers_slider.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.workers_label = ctk.CTkLabel(workers_frame, text="15")
        self.workers_label.pack(side="right", padx=10)
        self.workers_slider.configure(command=self.update_workers_label)
        
        # Botones
        buttons_frame = ctk.CTkFrame(panel)
        buttons_frame.pack(fill="x", pady=20)
        
        self.save_config_btn = ctk.CTkButton(
            buttons_frame,
            text="💾 Guardar Configuración",
            command=self.save_configuration
        )
        self.save_config_btn.pack(side="left", padx=20, pady=10)
        
        self.load_config_btn = ctk.CTkButton(
            buttons_frame,
            text="📂 Cargar Configuración",
            command=self.load_configuration
        )
        self.load_config_btn.pack(side="right", padx=20, pady=10)
    
    def old_create_download_panel(self):
        """Panel de descarga manual con análisis de archivos"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        self.panels["download"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="📥 Descarga Manual", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Filtros
        filters_frame = ctk.CTkFrame(panel)
        filters_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(filters_frame, text="🔍 Filtros de Descarga", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Empresa
        empresa_frame = ctk.CTkFrame(filters_frame)
        empresa_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(empresa_frame, text="Empresa:").pack(side="left", padx=10)
        self.empresa_combo = ctk.CTkComboBox(empresa_frame, values=["Cargando..."])
        self.empresa_combo.pack(side="right", padx=10, pady=10, fill="x", expand=True)
        
        # Fechas
        dates_frame = ctk.CTkFrame(filters_frame)
        dates_frame.pack(fill="x", padx=20, pady=5)
        
        # Fecha desde
        desde_frame = ctk.CTkFrame(dates_frame)
        desde_frame.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(desde_frame, text="Desde:").pack()
        self.fecha_desde = ctk.CTkEntry(desde_frame, placeholder_text="YYYY-MM-DD HH:MM")
        self.fecha_desde.pack(pady=5, fill="x")
        
        # Fecha hasta
        hasta_frame = ctk.CTkFrame(dates_frame)
        hasta_frame.pack(side="right", fill="x", expand=True, padx=5)
        ctk.CTkLabel(hasta_frame, text="Hasta:").pack()
        self.fecha_hasta = ctk.CTkEntry(hasta_frame, placeholder_text="YYYY-MM-DD HH:MM")
        self.fecha_hasta.pack(pady=5, fill="x")
        
        # Botones rápidos de fecha
        quick_dates_frame = ctk.CTkFrame(filters_frame)
        quick_dates_frame.pack(fill="x", padx=20, pady=10)
        
        quick_buttons = [
            ("📅 Última Hora", lambda: self.set_quick_date(1)),
            ("📅 Últimas 3 Horas", lambda: self.set_quick_date(3)),
            ("📅 Últimas 6 Horas", lambda: self.set_quick_date(6)),
            ("📅 Último Día", lambda: self.set_quick_date(24))
        ]
        
        for text, command in quick_buttons:
            btn = ctk.CTkButton(quick_dates_frame, text=text, command=command, width=120)
            btn.pack(side="left", padx=5, pady=5)
        
        # =========================================================================
        # NUEVA SECCIÓN: ANÁLISIS DE ARCHIVOS DESCARGADOS
        # =========================================================================
        
        # Crear tabla de análisis de archivos
        self.create_files_analysis_table(panel)
        
        # =========================================================================
        # FIN DE NUEVA SECCIÓN
        # =========================================================================
        
        # Botón de descarga (ahora al final)
        self.download_btn = ctk.CTkButton(
            panel,
            text="🚀 Iniciar Descarga",
            command=self.start_manual_download,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.download_btn.pack(pady=20, fill="x", padx=50)

    def create_download_panel(self):
        """Panel de descarga manual con análisis de archivos - Layout compacto"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        self.panels["download"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="📥 Descarga Manual", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Filtros - LAYOUT COMPACTO EN UNA SOLA FILA
        filters_frame = ctk.CTkFrame(panel)
        filters_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(filters_frame, text="🔍 Filtros de Descarga", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 5))
        
        # FILA ÚNICA CON EMPRESA Y FECHAS
        main_filters_frame = ctk.CTkFrame(filters_frame)
        main_filters_frame.pack(fill="x", padx=20, pady=(5, 10))
        
        # Empresa (1/3 del ancho)
        empresa_frame = ctk.CTkFrame(main_filters_frame)
        empresa_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(empresa_frame, text="Empresa:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 2))
        self.empresa_combo = ctk.CTkComboBox(empresa_frame, values=["Cargando..."], height=32)
        self.empresa_combo.pack(fill="x", padx=5, pady=(0, 5))
        
        # Fecha desde (1/3 del ancho)
        desde_frame = ctk.CTkFrame(main_filters_frame)
        desde_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        ctk.CTkLabel(desde_frame, text="Desde:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 2))
        self.fecha_desde = ctk.CTkEntry(desde_frame, placeholder_text="YYYY-MM-DD HH:MM", height=32)
        self.fecha_desde.pack(fill="x", padx=5, pady=(0, 5))
        
        # Fecha hasta (1/3 del ancho)
        hasta_frame = ctk.CTkFrame(main_filters_frame)
        hasta_frame.pack(side="left", fill="both", expand=True)
        ctk.CTkLabel(hasta_frame, text="Hasta:", font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 2))
        self.fecha_hasta = ctk.CTkEntry(hasta_frame, placeholder_text="YYYY-MM-DD HH:MM", height=32)
        self.fecha_hasta.pack(fill="x", padx=5, pady=(0, 5))
        
        # Botones rápidos de fecha - MÁS COMPACTOS
        quick_dates_frame = ctk.CTkFrame(filters_frame)
        quick_dates_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        ctk.CTkLabel(quick_dates_frame, text="⚡ Accesos rápidos:", font=ctk.CTkFont(size=12)).pack(side="left", padx=(10, 20))
        
        quick_buttons = [
            ("1h", lambda: self.set_quick_date(1)),
            ("3h", lambda: self.set_quick_date(3)),
            ("6h", lambda: self.set_quick_date(6)),
            ("24h", lambda: self.set_quick_date(24))
        ]
        
        for text, command in quick_buttons:
            btn = ctk.CTkButton(
                quick_dates_frame, 
                text=text, 
                command=command, 
                width=60, 
                height=28,
                font=ctk.CTkFont(size=11)
            )
            btn.pack(side="left", padx=3, pady=5)
        
        # =========================================================================
        # SECCIÓN: ANÁLISIS DE ARCHIVOS DESCARGADOS - MÁS COMPACTA
        # =========================================================================
        
        # Frame principal para análisis - ALTURA REDUCIDA
        analysis_frame = ctk.CTkFrame(panel)
        analysis_frame.pack(fill="both", pady=10, padx=20, expand=True)
        
        # Título y controles - MÁS COMPACTO
        header_frame = ctk.CTkFrame(analysis_frame)
        header_frame.pack(fill="x", pady=(10, 5), padx=10)
        
        ctk.CTkLabel(
            header_frame, 
            text="📊 Análisis de Archivos", 
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left", padx=10)
        
        # Estado en el centro
        self.files_status_label = ctk.CTkLabel(header_frame, text="💤 Sin datos", font=ctk.CTkFont(size=11))
        self.files_status_label.pack(side="left", padx=(20, 0))
        
        # Botón refresh más pequeño
        self.refresh_analysis_btn = ctk.CTkButton(
            header_frame,
            text="🔄",
            command=self.refresh_files_analysis,
            width=50,
            height=28,
            font=ctk.CTkFont(size=11)
        )
        self.refresh_analysis_btn.pack(side="right", padx=10)
        
        # Frame para la tabla con scroll - ALTURA FIJA MÁS PEQUEÑA
        table_container = ctk.CTkFrame(analysis_frame)
        table_container.pack(fill="x", pady=(0, 5), padx=10)
        
        # Crear tabla usando Treeview - MÁS COMPACTA
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores para que combine con customtkinter
        style.configure("Custom.Treeview", 
                    background="#2b2b2b",
                    foreground="white",
                    fieldbackground="#2b2b2b",
                    borderwidth=0,
                    rowheight=20)  # FILAS MÁS PEQUEÑAS
        style.configure("Custom.Treeview.Heading",
                    background="#1f538d",
                    foreground="white",
                    borderwidth=1,
                    font=("Arial", 8))  # FUENTE MÁS PEQUEÑA EN HEADERS
        
        # Crear Treeview con scrollbars - ALTURA FIJA
        table_frame = tk.Frame(table_container, height=150)  # ALTURA FIJA PEQUEÑA
        table_frame.pack(fill="x", padx=5, pady=5)
        table_frame.pack_propagate(False)  # MANTENER ALTURA FIJA
        
        # Definir columnas (Fecha + 24 horas)
        columns = ["Fecha"] + [f"{i:02d}" for i in range(24)]
        
        self.files_tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Custom.Treeview")
        
        # Configurar encabezados - MÁS COMPACTOS
        self.files_tree.heading("Fecha", text="Fecha")
        self.files_tree.column("Fecha", width=80, minwidth=70)
        
        for hour in range(24):
            col_name = f"{hour:02d}"
            self.files_tree.heading(col_name, text=col_name)
            self.files_tree.column(col_name, width=28, minwidth=25, anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.files_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tabla y scrollbars
        self.files_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configurar grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Información adicional - MÁS COMPACTA
        self.files_summary_label = ctk.CTkLabel(
            analysis_frame,
            text="📈 Total: 0 archivos en 0 fechas",
            font=ctk.CTkFont(size=11)
        )
        self.files_summary_label.pack(pady=(0, 10))
        
        # =========================================================================
        # FIN DE SECCIÓN OPTIMIZADA
        # =========================================================================
        
        # Botón de descarga - MÁS PROMINENTE
        self.download_btn = ctk.CTkButton(
            panel,
            text="🚀 Iniciar Descarga",
            command=self.start_manual_download,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.download_btn.pack(pady=15, fill="x", padx=50)
        
        # Cargar datos iniciales
        self.refresh_files_analysis()

    def create_automation_panel(self):
        """Panel de automatización"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        self.panels["automation"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="⏰ Automatización", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Estado de automatización
        status_frame = ctk.CTkFrame(panel)
        status_frame.pack(fill="x", pady=10)
        
        self.auto_status_label = ctk.CTkLabel(
            status_frame,
            text="🔴 Automatización DESACTIVADA",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.auto_status_label.pack(pady=10)
        
        # Control de automatización
        control_frame = ctk.CTkFrame(panel)
        control_frame.pack(fill="x", pady=10)
        
        self.auto_switch = ctk.CTkSwitch(
            control_frame,
            text="Activar descarga automática",
            command=self.toggle_automation
        )
        self.auto_switch.pack(pady=20)
        
        # Configuración de horarios
        schedule_frame = ctk.CTkFrame(panel)
        schedule_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(schedule_frame, text="⚙️ Configuración de Horarios", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Intervalo
        interval_frame = ctk.CTkFrame(schedule_frame)
        interval_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(interval_frame, text="Intervalo (horas):").pack(side="left", padx=10)
        self.interval_slider = ctk.CTkSlider(interval_frame, from_=1, to=24, number_of_steps=23)
        self.interval_slider.pack(side="left", padx=10, fill="x", expand=True)
        self.interval_label = ctk.CTkLabel(interval_frame, text="3")
        self.interval_label.pack(side="right", padx=10)
        self.interval_slider.configure(command=self.update_interval_label)
        
        # Horario activo
        hours_frame = ctk.CTkFrame(schedule_frame)
        hours_frame.pack(fill="x", padx=20, pady=5)
        
        start_frame = ctk.CTkFrame(hours_frame)
        start_frame.pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(start_frame, text="Hora inicio:").pack()
        self.start_hour_combo = ctk.CTkComboBox(start_frame, values=[f"{i:02d}:00" for i in range(24)])
        self.start_hour_combo.pack(pady=5)
        
        end_frame = ctk.CTkFrame(hours_frame)
        end_frame.pack(side="right", fill="x", expand=True, padx=5)
        ctk.CTkLabel(end_frame, text="Hora fin:").pack()
        self.end_hour_combo = ctk.CTkComboBox(end_frame, values=[f"{i:02d}:00" for i in range(24)])
        self.end_hour_combo.pack(pady=5)
        
        # Próxima ejecución
        self.next_run_label = ctk.CTkLabel(
            panel,
            text="⏱️ Próxima ejecución: No programada",
            font=ctk.CTkFont(size=14)
        )
        self.next_run_label.pack(pady=20)
        
        # 🆕 Configuraciones avanzadas
        advanced_frame = ctk.CTkFrame(panel)
        advanced_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(advanced_frame, text="🔧 Configuraciones Avanzadas", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        # Switch para descarga inicial
        self.initial_download_switch = ctk.CTkSwitch(
            advanced_frame,
            text="Descarga inicial al iniciar programa",
            command=self.toggle_initial_download
        )
        self.initial_download_switch.pack(pady=5)
        
        # Switch para scheduling inteligente
        self.smart_scheduling_switch = ctk.CTkSwitch(
            advanced_frame,
            text="No contar tiempo de descarga en intervalo",
            command=self.toggle_smart_scheduling
        )
        self.smart_scheduling_switch.pack(pady=5)
        
        # Delay de descarga inicial
        delay_frame = ctk.CTkFrame(advanced_frame)
        delay_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(delay_frame, text="Delay descarga inicial (min):").pack(side="left", padx=10)
        self.delay_slider = ctk.CTkSlider(delay_frame, from_=1, to=10, number_of_steps=9)
        self.delay_slider.pack(side="left", padx=10, fill="x", expand=True)
        self.delay_label = ctk.CTkLabel(delay_frame, text="2")
        self.delay_label.pack(side="right", padx=10)
        self.delay_slider.configure(command=self.update_delay_label)
    
    def create_monitoring_panel(self):
        """Panel de monitoreo"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        self.panels["monitoring"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="📊 Monitoreo", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Estado actual
        current_frame = ctk.CTkFrame(panel)
        current_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(current_frame, text="📈 Estado Actual", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.status_label = ctk.CTkLabel(current_frame, text="💤 Inactivo")
        self.status_label.pack(pady=5)
        
        # Progreso
        self.progress_bar = ctk.CTkProgressBar(current_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=10)
        self.progress_bar.set(0)
        
        self.progress_label = ctk.CTkLabel(current_frame, text="0%")
        self.progress_label.pack(pady=5)
        
        # Estadísticas
        stats_frame = ctk.CTkFrame(panel)
        stats_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(stats_frame, text="📊 Estadísticas", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.stats_text = ctk.CTkTextbox(stats_frame, height=200)
        self.stats_text.pack(fill="both", padx=20, pady=10, expand=True)
        self.stats_text.insert("0.0", "No hay estadísticas disponibles")
        
        # Botones de control
        control_frame = ctk.CTkFrame(panel)
        control_frame.pack(fill="x", pady=10)
        
        self.cancel_btn = ctk.CTkButton(
            control_frame,
            text="❌ Cancelar Descarga",
            command=self.cancel_download,
            state="disabled"
        )
        self.cancel_btn.pack(side="left", padx=20, pady=10)
        
        self.refresh_btn = ctk.CTkButton(
            control_frame,
            text="🔄 Actualizar",
            command=self.refresh_monitoring
        )
        self.refresh_btn.pack(side="right", padx=20, pady=10)
    
    def create_logs_panel(self):
        """Panel de logs"""
        panel = ctk.CTkFrame(self.main_frame)
        self.panels["logs"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="📝 Logs del Sistema", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Área de logs
        self.logs_text = ctk.CTkTextbox(panel, height=400)
        self.logs_text.pack(fill="both", padx=20, pady=10, expand=True)
        
        # Botones de logs
        logs_buttons_frame = ctk.CTkFrame(panel)
        logs_buttons_frame.pack(fill="x", pady=10)
        
        self.clear_logs_btn = ctk.CTkButton(
            logs_buttons_frame,
            text="🗑️ Limpiar Logs",
            command=self.clear_logs
        )
        self.clear_logs_btn.pack(side="left", padx=20, pady=10)
        
        self.export_logs_btn = ctk.CTkButton(
            logs_buttons_frame,
            text="💾 Exportar Logs",
            command=self.export_logs
        )
        self.export_logs_btn.pack(side="right", padx=20, pady=10)
    
    def create_debug_panel(self):
        """Panel de debug del sistema"""
        panel = ctk.CTkScrollableFrame(self.main_frame)
        self.panels["debug"] = panel
        
        # Título
        title = ctk.CTkLabel(panel, text="🔧 Debug del Sistema", font=ctk.CTkFont(size=24, weight="bold"))
        title.pack(pady=(0, 20))
        
        # Información del sistema
        info_frame = ctk.CTkFrame(panel)
        info_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(info_frame, text="ℹ️ Información del Sistema", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.debug_info_text = ctk.CTkTextbox(info_frame, height=150)
        self.debug_info_text.pack(fill="both", padx=20, pady=10, expand=True)
        
        # Resultados de debug
        results_frame = ctk.CTkFrame(panel)
        results_frame.pack(fill="x", pady=10)
        
        ctk.CTkLabel(results_frame, text="📊 Resultados de Debug", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=10)
        
        self.debug_results_text = ctk.CTkTextbox(results_frame, height=300)
        self.debug_results_text.pack(fill="both", padx=20, pady=10, expand=True)
        
        # Botones de debug
        debug_buttons_frame = ctk.CTkFrame(panel)
        debug_buttons_frame.pack(fill="x", pady=10)
        
        self.debug_full_btn = ctk.CTkButton(
            debug_buttons_frame,
            text="🚀 Debug Completo",
            command=self.run_full_debug,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.debug_full_btn.pack(side="left", padx=20, pady=10)
        
        self.debug_config_btn = ctk.CTkButton(
            debug_buttons_frame,
            text="⚙️ Debug Config",
            command=self.debug_config_only
        )
        self.debug_config_btn.pack(side="left", padx=10, pady=10)
        
        self.debug_gps_btn = ctk.CTkButton(
            debug_buttons_frame,
            text="🌐 Debug GPS",
            command=self.debug_gps_only
        )
        self.debug_gps_btn.pack(side="left", padx=10, pady=10)
        
        self.debug_api_btn = ctk.CTkButton(
            debug_buttons_frame,
            text="📡 Debug API",
            command=self.debug_api_only
        )
        self.debug_api_btn.pack(side="left", padx=10, pady=10)
        
        self.clear_debug_btn = ctk.CTkButton(
            debug_buttons_frame,
            text="🗑️ Limpiar",
            command=self.clear_debug_results
        )
        self.clear_debug_btn.pack(side="right", padx=20, pady=10)
        
        # Cargar información inicial
        self.update_debug_info()
    
    def create_status_area(self):
        """Crear área de estado en la parte inferior"""
        self.status_frame = ctk.CTkFrame(self.root, height=60)
        self.status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 20))
        
        self.connection_status = ctk.CTkLabel(self.status_frame, text="🔴 Desconectado")
        self.connection_status.pack(side="left", padx=20, pady=20)
        
        self.app_status = ctk.CTkLabel(self.status_frame, text="🟡 Inicializando...")
        self.app_status.pack(side="right", padx=20, pady=20)
    
    def show_panel(self, panel_name):
        """Mostrar panel específico"""
        # Ocultar todos los paneles
        for panel in self.panels.values():
            panel.grid_forget()
        
        # Mostrar panel seleccionado
        if panel_name in self.panels:
            self.panels[panel_name].grid(row=0, column=0, sticky="nsew")
        
        # Actualizar botones
        for key, btn in self.nav_buttons.items():
            if key == panel_name:
                btn.configure(fg_color=("gray75", "gray25"))
            else:
                btn.configure(fg_color=("gray80", "gray20"))
    
    def update_debug_info(self):
        """Actualizar información del sistema en el panel debug"""
        # Información de scheduler inteligente
        last_download_str = "NUNCA"
        if self.last_download_end_time:
            last_download_str = self.last_download_end_time.strftime('%Y-%m-%d %H:%M:%S')
        
        info = f"""🖥️ INFORMACIÓN DEL SISTEMA:

📂 Directorio de trabajo: {os.getcwd()}
🐍 Python: {sys.version.split()[0]}
📅 Fecha/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

⚙️ CONFIGURACIÓN ACTUAL:
• GPS Account: {get_config('gps.account', 'NO CONFIGURADO')}
• GPS URL: {get_config('gps.base_url', 'NO CONFIGURADO')}
• Base Directory: {get_config('download.base_directory', 'NO CONFIGURADO')}
• Max Workers: {get_config('download.max_workers', 'NO CONFIGURADO')}
• Session: {get_config('gps.current_session', 'NO CONFIGURADO')[:10] + '...' if get_config('gps.current_session') else 'NINGUNA'}

🤖 AUTOMATIZACIÓN INTELIGENTE:
• Automatización: {'✅ ACTIVA' if self.auto_download_enabled else '❌ DESACTIVA'}
• Descarga inicial: {'✅ ACTIVA' if get_config('automation.initial_download_on_startup', True) else '❌ DESACTIVA'}
• Scheduling inteligente: {'✅ ACTIVO' if get_config('automation.smart_scheduling', True) else '❌ DESACTIVO'}
• Intervalo: {get_config('automation.interval_hours', 3)} horas
• Horario: {get_config('automation.start_hour', 6):02d}:00 - {get_config('automation.end_hour', 22):02d}:00
• Delay inicial: {get_config('automation.initial_download_delay_minutes', 2)} minutos

🔧 ESTADO SCHEDULER:
• Scheduler running: {'✅ SÍ' if self.scheduler_running else '❌ NO'}
• Scheduler pausado: {'⏸️ SÍ' if self.scheduler_paused else '▶️ NO'}
• Descarga en progreso: {'🔄 SÍ' if self.download_in_progress else '💤 NO'}
• Descarga inicial hecha: {'✅ SÍ' if self.initial_download_done else '❌ NO'}
• Última descarga terminó: {last_download_str}

📊 OTROS:
• Empresas cargadas: {len(self.empresas_disponibles)}
• Job actual: {f'✅ {self.current_job.job_id}' if self.current_job else '❌ NINGUNO'}
"""
        
        self.debug_info_text.delete("0.0", tk.END)
        self.debug_info_text.insert("0.0", info)
    
    def debug_config_only(self):
        """Debug solo de configuración"""
        self.append_debug_result("\n🔍 DEBUGGING CONFIGURACIÓN...")
        
        result = f"""
⚙️ CONFIGURACIÓN GPS:
• Account: {get_config('gps.account', 'NO CONFIGURADO')}
• Password: {'***' if get_config('gps.password') else 'NO CONFIGURADO'}
• URL: {get_config('gps.base_url', 'NO CONFIGURADO')}
• Timeout: {get_config('gps.timeout', 'NO CONFIGURADO')}

📁 CONFIGURACIÓN DESCARGA:
• Base Directory: {get_config('download.base_directory', 'NO CONFIGURADO')}
• Max Workers: {get_config('download.max_workers', 'NO CONFIGURADO')}
• Concurrent Downloads: {get_config('download.concurrent_downloads', 'NO CONFIGURADO')}

⏰ CONFIGURACIÓN AUTOMATIZACIÓN:
• Enabled: {get_config('automation.enabled', 'NO CONFIGURADO')}
• Interval Hours: {get_config('automation.interval_hours', 'NO CONFIGURADO')}
• Start Hour: {get_config('automation.start_hour', 'NO CONFIGURADO')}
• End Hour: {get_config('automation.end_hour', 'NO CONFIGURADO')}

RESULTADO: {'✅ CONFIGURACIÓN OK' if all([get_config('gps.account'), get_config('gps.password'), get_config('gps.base_url')]) else '❌ FALTAN DATOS CRÍTICOS'}
"""
        self.append_debug_result(result)
    
    def debug_gps_only(self):
        """Debug solo de conexión GPS"""
        self.append_debug_result("\n🌐 DEBUGGING CONEXIÓN GPS...")
        
        try:
            # Verificar configuración
            account = get_config('gps.account')
            password = get_config('gps.password')
            url = get_config('gps.base_url')
            
            if not all([account, password, url]):
                self.append_debug_result("❌ FALTAN CREDENCIALES GPS")
                return
            
            # Intentar login
            self.append_debug_result(f"🔑 Intentando login con usuario: {account}")
            session = gps_login()
            
            if session:
                self.append_debug_result(f"✅ LOGIN EXITOSO: {session[:10]}...")
                
                # Probar obtener empresas
                try:
                    empresas, vehiculos = obtener_empresas_disponibles()
                    if empresas:
                        self.append_debug_result(f"✅ EMPRESAS OBTENIDAS: {len(empresas)} empresas, {len(vehiculos)} vehículos")
                        for emp in empresas[:3]:
                            self.append_debug_result(f"   • ID {emp.get('id')}: {emp.get('nm')} ({emp.get('vehicle_count', 0)} vehículos)")
                    else:
                        self.append_debug_result("❌ NO SE OBTUVIERON EMPRESAS")
                except Exception as e:
                    self.append_debug_result(f"❌ ERROR OBTENIENDO EMPRESAS: {e}")
            else:
                self.append_debug_result("❌ LOGIN FALLÓ - Verificar credenciales")
                
        except Exception as e:
            self.append_debug_result(f"💥 EXCEPCIÓN EN LOGIN GPS: {e}")
    
    def debug_api_only(self):
        """Debug solo de API de fotos"""
        self.append_debug_result("\n📡 DEBUGGING API DE FOTOS...")
        
        try:
            # Verificar session GPS
            session = get_config('gps.current_session')
            if not session:
                self.append_debug_result("❌ NO HAY SESIÓN GPS ACTIVA")
                return
            
            # Test query simple
            now = datetime.now()
            end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            start_time = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            self.append_debug_result(f"📅 Test periodo: {start_time} → {end_time}")
            
            result = query_security_photos(start_time, end_time, 1, 5)
            
            if result and result.get('result') == 0:
                pagination = result.get('pagination', {})
                total = pagination.get('totalRecords', 0)
                pages = pagination.get('totalPages', 0)
                self.append_debug_result(f"✅ API RESPONDE: {total} fotos, {pages} páginas")
                
                # Mostrar algunas fotos de ejemplo
                photos = result.get('infos', [])
                if photos:
                    self.append_debug_result(f"📸 MUESTRA DE FOTOS ({len(photos)}):")
                    for i, photo in enumerate(photos[:3]):
                        veh = photo.get('vehiIdno', 'N/A')
                        dev = photo.get('devIdno', 'N/A')
                        time_str = photo.get('fileTimeStr', 'N/A')
                        self.append_debug_result(f"   • Foto {i+1}: Veh={veh}, Dev={dev}, Time={time_str}")
                else:
                    self.append_debug_result("ℹ️ NO HAY FOTOS EN LA RESPUESTA")
            else:
                error_msg = result.get('msg', 'Error desconocido') if result else 'Sin respuesta'
                self.append_debug_result(f"❌ API FALLÓ: {error_msg}")
                
        except Exception as e:
            self.append_debug_result(f"💥 EXCEPCIÓN EN TEST API: {e}")
    
    def run_full_debug(self):
        """Debug completo del sistema"""
        self.clear_debug_results()
        self.append_debug_result("🚀 INICIANDO DEBUG COMPLETO DEL SISTEMA")
        self.append_debug_result("=" * 60)
        
        # 1. Debug configuración
        self.debug_config_only()
        
        # 2. Debug GPS
        self.debug_gps_only()
        
        # 3. Debug API
        self.debug_api_only()
        
        # 4. Test empresa específica
        self.append_debug_result("\n🏢 TESTING FILTRO POR EMPRESA...")
        try:
            if self.empresas_disponibles:
                empresa_test = self.empresas_disponibles[0]
                empresa_id = str(empresa_test.get('id'))
                self.append_debug_result(f"🎯 Testing empresa: {empresa_test.get('nm')} (ID: {empresa_id})")
                
                empresa_filter = obtener_vehiculos_por_empresa(empresa_id)
                if empresa_filter:
                    info = empresa_filter['empresa_info']
                    self.append_debug_result(f"✅ FILTRO EMPRESA OK: {info['nombre']} - {info['total_vehiculos']} vehículos")
                    self.append_debug_result(f"   • VehiIdnos: {len(empresa_filter['vehiIdnos'])}")
                    self.append_debug_result(f"   • DevIdnos: {len(empresa_filter['devIdnos'])}")
                else:
                    self.append_debug_result("❌ FILTRO EMPRESA FALLÓ")
            else:
                self.append_debug_result("⚠️ NO HAY EMPRESAS PARA TESTEAR")
        except Exception as e:
            self.append_debug_result(f"💥 ERROR EN TEST EMPRESA: {e}")
        
        # Resultado final
        self.append_debug_result("\n" + "=" * 60)
        self.append_debug_result("🎉 DEBUG COMPLETO FINALIZADO")
        
        # Actualizar info del sistema
        self.update_debug_info()
    
    def clear_debug_results(self):
        """Limpiar resultados de debug"""
        self.debug_results_text.delete("0.0", tk.END)
    
    def append_debug_result(self, text):
        """Agregar texto a los resultados de debug"""
        self.debug_results_text.insert(tk.END, text + "\n")
        self.debug_results_text.see(tk.END)
        self.root.update()  # Forzar actualización de GUI
    
    def debug_download_system(self):
        """Debug completo del sistema de descarga (devuelve True/False)"""
        print("\n" + "="*60)
        print("🚀 INICIANDO DEBUG COMPLETO DEL SISTEMA")
        print("="*60)
        
        # 1. Config
        print("\n1️⃣ CONFIGURACIÓN:")
        account = get_config('gps.account', 'NO CONFIGURADO')
        password = get_config('gps.password', 'NO CONFIGURADO')
        url = get_config('gps.base_url', 'NO CONFIGURADO')
        
        print(f"   GPS Account: {account}")
        print(f"   GPS URL: {url}")
        print(f"   Base Dir: {get_config('download.base_directory', 'NO CONFIGURADO')}")
        
        if not all([account, password, url]):
            print("   ❌ FALTAN CONFIGURACIONES CRÍTICAS")
            return False
        
        # 2. Login GPS
        print("\n2️⃣ LOGIN GPS:")
        try:
            session = gps_login()
            if session:
                print(f"   ✅ Login exitoso: {session[:10]}...")
            else:
                print("   ❌ Login falló - revisar credenciales")
                return False
        except Exception as e:
            print(f"   💥 Excepción en login: {e}")
            return False
        
        # 3. Empresas
        print("\n3️⃣ EMPRESAS DISPONIBLES:")
        try:
            empresas, vehiculos = obtener_empresas_disponibles()
            if empresas:
                print(f"   ✅ {len(empresas)} empresas encontradas")
                for emp in empresas[:3]:
                    print(f"      - ID {emp.get('id')}: {emp.get('nm')} ({emp.get('vehicle_count', 0)} vehículos)")
            else:
                print("   ❌ No se encontraron empresas")
                return False
        except Exception as e:
            print(f"   💥 Error obteniendo empresas: {e}")
            return False
        
        # 4. Test descarga simple
        print("\n4️⃣ TEST DESCARGA:")
        try:
            now = datetime.now()
            end_time = now.strftime("%Y-%m-%d %H:%M:%S")
            start_time = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            
            print(f"   Periodo test: {start_time} → {end_time}")
            
            result = query_security_photos(start_time, end_time, 1, 5)
            
            if result and result.get('result') == 0:
                total = result.get('pagination', {}).get('totalRecords', 0)
                print(f"   ✅ API responde: {total} fotos encontradas")
            else:
                print(f"   ❌ API falló: {result}")
                return False
                
        except Exception as e:
            print(f"   💥 Error en test API: {e}")
            return False
        
        print("\n🎉 DEBUG COMPLETADO - Sistema funcional!")
        return True
  
    def schedule_initial_download(self):
        """Programar descarga inicial con delay"""
        delay_minutes = get_config('automation.initial_download_delay_minutes', 2)
        self.logger.info(f"🕐 Descarga inicial programada en {delay_minutes} minutos")
        
        def run_initial():
            time.sleep(delay_minutes * 60)  # Convertir a segundos
            if not self.initial_download_done and self.auto_download_enabled:
                self.logger.info("🚀 Ejecutando descarga inicial automática")
                self.run_initial_download()
        
        # Ejecutar en thread separado para no bloquear GUI
        threading.Thread(target=run_initial, daemon=True).start()
    
    def run_initial_download(self):
        """Ejecutar descarga inicial automática"""
        try:
            # Verificar que no hay descarga en curso
            if self.download_in_progress:
                self.logger.warning("⚠️ Descarga inicial omitida: hay descarga en curso")
                return
            
            # Verificar horario activo
            now = datetime.now()
            start_hour = get_config('automation.start_hour', 6)
            end_hour = get_config('automation.end_hour', 22)
            
            if not (start_hour <= now.hour <= end_hour):
                self.logger.info(f"⏰ Descarga inicial omitida: fuera del horario ({now.hour}h)")
                return
            
            # Marcar como iniciada
            self.initial_download_done = True
            
            # Configurar parámetros de descarga
            hours_back = get_config('filters.default_hours_back', 2)
            end_time = now
            start_time = now - timedelta(hours=hours_back)
            
            # 🔧 FIX: Convertir empresa_id a string si es necesario
            empresa_id_raw = get_config('filters.default_empresa_id')
            empresa_id = None
            if empresa_id_raw is not None:
                empresa_id = str(empresa_id_raw)  # Convertir a string siempre
            
            self.logger.info(f"🤖 Iniciando descarga inicial: {hours_back}h atrás, empresa: {empresa_id or 'Todas'}")
            
            # Marcar descarga en progreso
            self.download_in_progress = True
            
            # Pausar scheduler durante descarga inicial
            if get_config('automation.smart_scheduling', True):
                self.pause_scheduler()
            
            # Iniciar descarga
            self.current_job = start_download_job(
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"),
                empresa_id
            )
            
            # Configurar callbacks
            self.current_job.set_callbacks(
                progress_callback=self.on_download_progress,
                completion_callback=self.on_download_complete_smart,
                error_callback=self.on_download_error_smart
            )
            
            # Actualizar GUI si estamos en panel de monitoreo
            self.root.after(0, lambda: self.refresh_monitoring())
            
        except Exception as e:
            self.logger.error(f"❌ Error en descarga inicial: {e}")
            self.download_in_progress = False
            if get_config('automation.smart_scheduling', True):
                self.resume_scheduler()
    
    def pause_scheduler(self):
        """Pausar scheduler durante descarga"""
        self.scheduler_paused = True
        self.logger.info("⏸️ Scheduler pausado durante descarga")
    
    def resume_scheduler(self):
        """Reanudar scheduler después de descarga"""
        self.scheduler_paused = False
        self.logger.info("▶️ Scheduler reanudado")
        
        # Recalcular próxima ejecución basada en fin de descarga
        self.calculate_next_run_smart()
    
    def calculate_next_run_smart(self):
        """Calcular próxima ejecución considerando fin de última descarga"""
        interval = get_config('automation.interval_hours', 3)
        start_hour = get_config('automation.start_hour', 6)
        end_hour = get_config('automation.end_hour', 22)
        
        now = datetime.now()
        
        # Si hay timestamp de fin de descarga y smart scheduling está habilitado
        if (self.last_download_end_time and 
            get_config('automation.smart_scheduling', True)):
            
            # Calcular próxima ejecución desde fin de última descarga
            next_run = self.last_download_end_time + timedelta(hours=interval)
            
            # Verificar que esté dentro del horario activo
            if next_run.hour < start_hour:
                # Si es muy temprano, programar para start_hour del mismo día
                next_run = next_run.replace(hour=start_hour, minute=0, second=0, microsecond=0)
            elif next_run.hour > end_hour:
                # Si es muy tarde, programar para start_hour del día siguiente
                next_run = (next_run + timedelta(days=1)).replace(hour=start_hour, minute=0, second=0, microsecond=0)
            
            self.logger.info(f"📅 Próxima ejecución calculada desde fin de descarga: {next_run}")
            
        else:
            # Lógica tradicional si no hay descarga previa o smart scheduling deshabilitado
            if start_hour <= now.hour <= end_hour:
                next_run = now + timedelta(hours=interval)
            else:
                tomorrow = now.replace(hour=start_hour, minute=0, second=0, microsecond=0)
                if now.hour >= end_hour:
                    tomorrow += timedelta(days=1)
                next_run = tomorrow
        
        # Actualizar GUI
        self.next_run_label.configure(text=f"⏱️ Próxima ejecución: {next_run.strftime('%d/%m/%Y %H:%M')}")
        
        return next_run
    
    def on_download_complete_smart(self, job):
        """Callback de descarga completada con lógica inteligente"""
        # Marcar fin de descarga
        self.download_in_progress = False
        self.last_download_end_time = datetime.now()
        
        self.logger.info(f"✅ Descarga completada a las {self.last_download_end_time.strftime('%H:%M:%S')}")
        
        # Reanudar scheduler si está pausado
        if self.scheduler_paused and get_config('automation.smart_scheduling', True):
            self.resume_scheduler()
        
        # Llamar callback original
        self.on_download_complete(job)
    
    def on_download_error_smart(self, job, error_message):
        """Callback de error con lógica inteligente"""
        # Marcar fin de descarga (aunque haya fallado)
        self.download_in_progress = False
        
        # Reanudar scheduler si está pausado
        if self.scheduler_paused and get_config('automation.smart_scheduling', True):
            self.resume_scheduler()
        
        # Llamar callback original
        self.on_download_error(job, error_message)
    
    def load_initial_data(self):
        """Cargar datos iniciales"""
        # Cargar configuración en GUI
        self.user_entry.insert(0, get_config('gps.account', ''))
        self.pass_entry.insert(0, get_config('gps.password', ''))
        self.server_entry.insert(0, get_config('gps.base_url', ''))
        self.dir_entry.insert(0, get_config('download.base_directory', ''))
        self.workers_slider.set(get_config('download.max_workers', 15))
        self.update_workers_label(get_config('download.max_workers', 15))
        
        # Configuración de automatización
        self.interval_slider.set(get_config('automation.interval_hours', 3))
        self.update_interval_label(get_config('automation.interval_hours', 3))
        self.start_hour_combo.set(f"{get_config('automation.start_hour', 6):02d}:00")
        self.end_hour_combo.set(f"{get_config('automation.end_hour', 22):02d}:00")
        
        # 🆕 Configuraciones avanzadas
        if get_config('automation.initial_download_on_startup', True):
            self.initial_download_switch.select()
        
        if get_config('automation.smart_scheduling', True):
            self.smart_scheduling_switch.select()
        
        self.delay_slider.set(get_config('automation.initial_download_delay_minutes', 2))
        self.update_delay_label(get_config('automation.initial_download_delay_minutes', 2))
        
        if get_config('automation.enabled', False):
            self.auto_switch.select()
            self.update_auto_status(True)
        
        # Cargar empresas
        self.load_empresas()
        
        # Establecer fechas por defecto
        self.set_quick_date(6)  # Últimas 6 horas por defecto
        
        # Actualizar estado
        self.app_status.configure(text="✅ Listo")
    
    def load_empresas(self):
        """Cargar lista de empresas disponibles"""
        def load_async():
            try:
                empresas, _ = obtener_empresas_disponibles()
                self.empresas_disponibles = empresas
                
                empresa_names = ["🌐 Todas las empresas"]
                for empresa in empresas:
                    name = f"🏢 {empresa.get('nm', 'Sin nombre')} ({empresa.get('vehicle_count', 0)} vehículos)"
                    empresa_names.append(name)
                
                # Actualizar GUI en thread principal
                self.root.after(0, lambda: self.empresa_combo.configure(values=empresa_names))
                self.root.after(0, lambda: self.empresa_combo.set(empresa_names[0]))
                
                if empresas:
                    self.connection_status.configure(text="🟢 Conectado GPS")
                    self.logger.info(f"✅ Cargadas {len(empresas)} empresas")
                else:
                    self.connection_status.configure(text="🟡 GPS Sin datos")
                    
            except Exception as e:
                self.logger.error(f"❌ Error cargando empresas: {e}")
                self.root.after(0, lambda: self.connection_status.configure(text="🔴 Error GPS"))
        
        threading.Thread(target=load_async, daemon=True).start()

    def test_gps_connection(self):
        """Probar conexión GPS"""
        def test_async():
            try:
                # Guardar credenciales temporalmente
                set_config('gps.account', self.user_entry.get())
                set_config('gps.password', self.pass_entry.get())
                set_config('gps.base_url', self.server_entry.get())
                
                # Probar login
                session = gps_login()
                if session:
                    self.root.after(0, lambda: messagebox.showinfo("Éxito", "✅ Conexión GPS exitosa"))
                    self.root.after(0, lambda: self.connection_status.configure(text="🟢 Conectado GPS"))
                    self.load_empresas()  # Recargar empresas
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "❌ Error en conexión GPS"))
                    self.root.after(0, lambda: self.connection_status.configure(text="🔴 Error GPS"))
                    
            except Exception as e:
                self.logger.error(f"❌ Error probando conexión: {e}")
                self.root.after(0, lambda: messagebox.showerror("Error", f"❌ Error: {str(e)}"))
        
        threading.Thread(target=test_async, daemon=True).start()
    
    def browse_directory(self):
        """Examinar directorio de descarga"""
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)
    
    def update_delay_label(self, value):
        """Actualizar label de delay"""
        self.delay_label.configure(text=f"{int(value)}")
    
    def toggle_initial_download(self):
        """Activar/desactivar descarga inicial"""
        enabled = self.initial_download_switch.get() == 1
        set_config('automation.initial_download_on_startup', enabled)
        save_config()
        self.logger.info(f"📥 Descarga inicial: {'✅ ACTIVADA' if enabled else '❌ DESACTIVADA'}")
    
    def toggle_smart_scheduling(self):
        """Activar/desactivar scheduling inteligente"""
        enabled = self.smart_scheduling_switch.get() == 1
        set_config('automation.smart_scheduling', enabled)
        save_config()
        self.logger.info(f"🧠 Scheduling inteligente: {'✅ ACTIVADO' if enabled else '❌ DESACTIVADO'}")
    
    def update_workers_label(self, value):
        """Actualizar label de workers"""
        self.workers_label.configure(text=str(int(value)))
    
    def update_interval_label(self, value):
        """Actualizar label de intervalo"""
        self.interval_label.configure(text=f"{int(value)}")
    
    def save_configuration(self):
        """Guardar configuración"""
        try:
            # Actualizar configuración
            set_config('gps.account', self.user_entry.get())
            set_config('gps.password', self.pass_entry.get())
            set_config('gps.base_url', self.server_entry.get())
            set_config('download.base_directory', self.dir_entry.get())
            set_config('download.max_workers', int(self.workers_slider.get()))
            set_config('automation.interval_hours', int(self.interval_slider.get()))
            set_config('automation.start_hour', int(self.start_hour_combo.get().split(':')[0]))
            set_config('automation.end_hour', int(self.end_hour_combo.get().split(':')[0]))
            
            # 🆕 Configuraciones avanzadas
            set_config('automation.initial_download_delay_minutes', int(self.delay_slider.get()))
            
            # Guardar archivo
            if save_config():
                messagebox.showinfo("Éxito", "✅ Configuración guardada correctamente")
                self.logger.info("✅ Configuración guardada")
            else:
                messagebox.showerror("Error", "❌ Error guardando configuración")
                
        except Exception as e:
            self.logger.error(f"❌ Error guardando configuración: {e}")
            messagebox.showerror("Error", f"❌ Error: {str(e)}")
    
    def load_configuration(self):
        """Cargar configuración"""
        if load_config():
            self.load_initial_data()
            messagebox.showinfo("Éxito", "✅ Configuración cargada correctamente")
        else:
            messagebox.showerror("Error", "❌ Error cargando configuración")
    
    def set_quick_date(self, hours_back):
        """Establecer fecha rápida"""
        now = datetime.now()
        start = now - timedelta(hours=hours_back)
        
        self.fecha_desde.delete(0, tk.END)
        self.fecha_desde.insert(0, start.strftime("%Y-%m-%d %H:%M"))
        
        self.fecha_hasta.delete(0, tk.END)
        self.fecha_hasta.insert(0, now.strftime("%Y-%m-%d %H:%M"))
    
    def stop_scheduler(self):
        """Detener scheduler"""
        self.scheduler_running = False
        self.scheduler_paused = False
        schedule.clear()
        if self.scheduler_thread:
            self.scheduler_thread = None
        
        self.logger.info("⏰ Scheduler de automatización detenido")
    
    def start_manual_download(self):
        """Iniciar descarga manual CON DEBUG INTEGRADO y lógica inteligente"""
        try:
            # 🔧 DEBUG COMPLETO ANTES DE INICIAR
            print("\n" + "🔍" * 30)
            print("INICIANDO DEBUG PRE-DESCARGA")
            print("🔍" * 30)
            
            if not self.debug_download_system():
                messagebox.showerror("Error", "❌ Sistema no está listo para descarga. Ver logs de debug.")
                return
            
            print("✅ DEBUG COMPLETO - Sistema listo para descarga")
            
            # Verificar si hay descarga en curso
            if self.download_in_progress:
                messagebox.showerror("Error", "❌ Ya hay una descarga en curso")
                return
            
            # Validar datos de entrada
            if not self.fecha_desde.get() or not self.fecha_hasta.get():
                messagebox.showerror("Error", "❌ Debe especificar fechas")
                return
            
            # Obtener empresa seleccionada
            empresa_id = None
            empresa_sel = self.empresa_combo.get()
            if empresa_sel != "🌐 Todas las empresas":
                # Buscar ID de empresa por nombre
                for empresa in self.empresas_disponibles:
                    if empresa.get('nm') in empresa_sel:
                        empresa_id = str(empresa.get('id'))
                        break
            
            # Formatear fechas
            begin_time = f"{self.fecha_desde.get()}:00"
            end_time = f"{self.fecha_hasta.get()}:59"
            
            print(f"\n🎯 PARÁMETROS DE DESCARGA:")
            print(f"   • Begin time: {begin_time}")
            print(f"   • End time: {end_time}")
            print(f"   • Empresa ID: {empresa_id or 'Todas las empresas'}")
            
            # Marcar descarga manual en progreso
            self.download_in_progress = True
            
            # Pausar scheduler durante descarga manual si está habilitado
            if (self.auto_download_enabled and 
                get_config('automation.smart_scheduling', True)):
                self.pause_scheduler()
            
            # Iniciar descarga CON MANEJO DE ERRORES DETALLADO
            try:
                print(f"\n🚀 Llamando start_download_job...")
                self.current_job = start_download_job(begin_time, end_time, empresa_id)
                print(f"✅ Job creado exitosamente: {self.current_job.job_id}")
                
                # Configurar callbacks con lógica inteligente para descarga manual
                self.current_job.set_callbacks(
                    progress_callback=self.on_download_progress,
                    completion_callback=self.on_manual_download_complete,
                    error_callback=self.on_manual_download_error
                )
                
                # Actualizar GUI
                self.download_btn.configure(text="⏳ Descargando...", state="disabled")
                self.cancel_btn.configure(state="normal")
                self.show_panel("monitoring")
                
                self.logger.info(f"🚀 Descarga manual iniciada: {empresa_id or 'Todas las empresas'}")
                
            except Exception as job_error:
                print(f"💥 ERROR EN start_download_job: {job_error}")
                print(f"   Tipo: {type(job_error).__name__}")
                print(f"   Args: {job_error.args}")
                
                # Restaurar estado en caso de error
                self.download_in_progress = False
                if (self.auto_download_enabled and 
                    self.scheduler_paused and 
                    get_config('automation.smart_scheduling', True)):
                    self.resume_scheduler()
                
                # Mostrar error detallado
                error_msg = f"Error en start_download_job:\n{str(job_error)}"
                messagebox.showerror("Error de Descarga", error_msg)
                self.logger.error(f"❌ Error en start_download_job: {job_error}", exc_info=True)
                return
            
        except Exception as e:
            print(f"💥 ERROR GENERAL EN start_manual_download: {e}")
            self.download_in_progress = False
            if (self.auto_download_enabled and 
                self.scheduler_paused and 
                get_config('automation.smart_scheduling', True)):
                self.resume_scheduler()
            self.logger.error(f"❌ Error general en descarga: {e}", exc_info=True)
            messagebox.showerror("Error", f"❌ Error: {str(e)}")
    
    def on_manual_download_complete(self, job):
        """Callback específico para descarga manual completada"""
        # Marcar fin de descarga manual
        self.download_in_progress = False
        
        # No actualizar last_download_end_time para descargas manuales
        # para no afectar el scheduling automático
        
        # Reanudar scheduler si está pausado (sin recalcular timing)
        if (self.auto_download_enabled and 
            self.scheduler_paused and 
            get_config('automation.smart_scheduling', True)):
            self.scheduler_paused = False
            self.logger.info("▶️ Scheduler reanudado después de descarga manual")
        
        # Llamar callback original
        self.on_download_complete(job)
        
        self.logger.info("✅ Descarga manual completada - scheduler reanudado")
    
    def on_manual_download_error(self, job, error_message):
        """Callback específico para error en descarga manual"""
        # Marcar fin de descarga manual
        self.download_in_progress = False
        
        # Reanudar scheduler si está pausado
        if (self.auto_download_enabled and 
            self.scheduler_paused and 
            get_config('automation.smart_scheduling', True)):
            self.scheduler_paused = False
            self.logger.info("▶️ Scheduler reanudado después de error en descarga manual")
        
        # Llamar callback original
        self.on_download_error(job, error_message)
    
    def cancel_download(self):
        """Cancelar descarga actual"""
        if self.current_job:
            self.current_job.status = 'cancelled'
            self.current_job = None
            
            # Marcar fin de descarga
            self.download_in_progress = False
            
            # Reanudar scheduler si está pausado
            if (self.auto_download_enabled and 
                self.scheduler_paused and 
                get_config('automation.smart_scheduling', True)):
                self.scheduler_paused = False
                self.logger.info("▶️ Scheduler reanudado después de cancelación")
            
            self.download_btn.configure(text="🚀 Iniciar Descarga", state="normal")
            self.cancel_btn.configure(state="disabled")
            self.progress_bar.set(0)
            self.status_label.configure(text="❌ Descarga cancelada")
            
            self.logger.info("❌ Descarga cancelada por usuario")
    
    def toggle_automation(self):
        """Activar/desactivar automatización"""
        enabled = self.auto_switch.get() == 1
        set_config('automation.enabled', enabled)
        save_config()
        
        self.auto_download_enabled = enabled
        
        if enabled:
            self.start_scheduler()
            # Programar descarga inicial si está habilitada
            if (get_config('automation.initial_download_on_startup', True) and
                not self.initial_download_done):
                self.schedule_initial_download()
        else:
            self.stop_scheduler()
        
        self.update_auto_status(enabled)
    
    def update_auto_status(self, enabled):
        """Actualizar estado de automatización"""
        if enabled:
            self.auto_status_label.configure(text="🟢 Automatización ACTIVADA")
            self.calculate_next_run_smart()
        else:
            self.auto_status_label.configure(text="🔴 Automatización DESACTIVADA")
            self.next_run_label.configure(text="⏱️ Próxima ejecución: No programada")
    
    def calculate_next_run(self):
        """Método legacy - usar calculate_next_run_smart en su lugar"""
        return self.calculate_next_run_smart()
    
    def start_scheduler(self):
        """Iniciar scheduler de automatización con lógica inteligente"""
        if self.scheduler_running:
            return
        
        self.scheduler_running = True
        
        def scheduler_worker():
            # Configurar schedule
            interval = get_config('automation.interval_hours', 3)
            schedule.every(interval).hours.do(self.auto_download_smart)
            
            while self.scheduler_running:
                # Solo ejecutar si scheduler no está pausado
                if not self.scheduler_paused:
                    schedule.run_pending()
                else:
                    self.logger.debug("⏸️ Scheduler pausado, omitiendo verificación")
                
                time.sleep(60)  # Verificar cada minuto
        
        self.scheduler_thread = threading.Thread(target=scheduler_worker, daemon=True)
        self.scheduler_thread.start()
        
        self.logger.info("⏰ Scheduler inteligente iniciado")
    
    def auto_download_smart(self):
        """Ejecutar descarga automática con lógica inteligente"""
        try:
            # Verificar si hay descarga en curso
            if self.download_in_progress:
                self.logger.info("⚠️ Descarga automática omitida: descarga en curso")
                return
            
            # Verificar horario
            now = datetime.now()
            start_hour = get_config('automation.start_hour', 6)
            end_hour = get_config('automation.end_hour', 22)
            
            if not (start_hour <= now.hour <= end_hour):
                self.logger.info(f"⏰ Fuera del horario de automatización: {now.hour}h")
                return
            
            # Marcar descarga en progreso
            self.download_in_progress = True
            
            # Pausar scheduler durante descarga
            if get_config('automation.smart_scheduling', True):
                self.pause_scheduler()
            
            # Configurar descarga automática
            hours_back = get_config('filters.default_hours_back', 6)
            end_time = now
            start_time = now - timedelta(hours=hours_back)
            
            # 🔧 FIX: Convertir empresa_id a string si es necesario
            empresa_id_raw = get_config('filters.default_empresa_id')
            empresa_id = None
            if empresa_id_raw is not None:
                empresa_id = str(empresa_id_raw)  # Convertir a string siempre
            
            # Iniciar descarga
            self.current_job = start_download_job(
                start_time.strftime("%Y-%m-%d %H:%M:%S"),
                end_time.strftime("%Y-%m-%d %H:%M:%S"),
                empresa_id
            )
            
            # Configurar callbacks inteligentes
            self.current_job.set_callbacks(
                progress_callback=self.on_download_progress,
                completion_callback=self.on_download_complete_smart,
                error_callback=self.on_download_error_smart
            )
            
            self.logger.info(f"🤖 Descarga automática iniciada: {hours_back}h atrás, empresa: {empresa_id or 'Todas'}")
            
            # Actualizar GUI si estamos en panel de monitoreo
            self.root.after(0, lambda: self.refresh_monitoring())
            
        except Exception as e:
            self.logger.error(f"❌ Error en descarga automática: {e}")
            self.download_in_progress = False
            if self.scheduler_paused and get_config('automation.smart_scheduling', True):
                self.resume_scheduler()


    def on_download_progress(self, job):
        """Callback de progreso de descarga"""
        def update_gui():
            try:
                # Actualizar barra de progreso
                progress_value = min(1.0, max(0.0, job.progress / 100))
                self.progress_bar.set(progress_value)
                
                # Actualizar label de porcentaje
                self.progress_label.configure(text=f"{job.progress:.1f}%")
                
                # Actualizar mensaje de estado
                if hasattr(job, 'message') and job.message:
                    self.status_label.configure(text=job.message)
                
                # Información adicional si está disponible
                if hasattr(job, 'downloaded_photos') and hasattr(job, 'total_photos'):
                    if job.total_photos > 0:
                        status_text = f"📥 {job.downloaded_photos}/{job.total_photos} fotos"
                        if hasattr(job, 'message'):
                            status_text = f"{job.message} | {status_text}"
                        self.status_label.configure(text=status_text)
                
                # Log de progreso cada 10%
                if hasattr(job, 'progress') and job.progress % 10 == 0:
                    self.logger.debug(f"📊 Progreso: {job.progress:.1f}% - {job.message}")
                    
            except Exception as e:
                self.logger.error(f"❌ Error actualizando progreso GUI: {e}")
        
        # Ejecutar actualización en thread principal de GUI
        self.root.after(0, update_gui)


    def on_download_complete(self, job):
        """Callback de descarga completada - MODIFICAR EXISTENTE"""
        def update_gui():
            self.progress_bar.set(1.0)
            self.progress_label.configure(text="100%")
            self.status_label.configure(text="✅ Descarga completada")
            
            if job.stats:
                stats_text = f"""
    📊 ESTADÍSTICAS DE DESCARGA:

    ✅ Fotos descargadas: {job.stats.get('descargadas', 0)}
    ⏭️ Ya existían: {job.stats.get('ya_existen', 0)}
    📄 Total disponibles: {job.stats.get('total_disponibles', 0)}
    🚌 Vehículos únicos: {job.stats.get('vehiculos_count', 0)}
    💥 Errores: {job.stats.get('errores', 0)}
    ⏱️ Duración: {job.stats.get('duration', 0):.1f} segundos
    🚀 Velocidad: {job.stats.get('velocidad_promedio', 0):.1f} fotos/seg
    """
                self.stats_text.delete("0.0", tk.END)
                self.stats_text.insert("0.0", stats_text)
            
            self.download_btn.configure(text="🚀 Iniciar Descarga", state="normal")
            self.cancel_btn.configure(state="disabled")
            
            # Calcular próxima ejecución automática
            self.calculate_next_run()
            
            # 🆕 NUEVO: Actualizar análisis de archivos después de descarga exitosa
            if job.stats and job.stats.get('descargadas', 0) > 0:
                self.logger.info("🔄 Actualizando análisis de archivos post-descarga")
                self.refresh_files_analysis()
        
        self.root.after(0, update_gui)
        self.logger.info(f"✅ Descarga completada: {job.stats.get('total_disponibles', 0)} fotos")

    def on_download_error(self, job, error_message):
        """Callback de error en descarga"""
        def update_gui():
            self.status_label.configure(text=f"❌ Error: {error_message}")
            self.download_btn.configure(text="🚀 Iniciar Descarga", state="normal")
            self.cancel_btn.configure(state="disabled")
            self.progress_bar.set(0)
            
            messagebox.showerror("Error en Descarga", f"❌ {error_message}")
        
        self.root.after(0, update_gui)
        self.logger.error(f"❌ Error en descarga: {error_message}")
    
    def refresh_monitoring(self):
        """Actualizar panel de monitoreo"""
        if self.current_job:
            self.progress_bar.set(self.current_job.progress / 100)
            self.progress_label.configure(text=f"{self.current_job.progress:.1f}%")
            self.status_label.configure(text=self.current_job.message)
            
            if self.current_job.status == 'running':
                self.cancel_btn.configure(state="normal")
            else:
                self.cancel_btn.configure(state="disabled")
        else:
            self.status_label.configure(text="💤 Inactivo")
            self.progress_bar.set(0)
            self.progress_label.configure(text="0%")
            self.cancel_btn.configure(state="disabled")
    
    def clear_logs(self):
        """Limpiar logs"""
        self.logs_text.delete("0.0", tk.END)
        self.logs_text.insert("0.0", "Logs limpiados\n")
    
    def export_logs(self):
        """Exportar logs a archivo"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                content = self.logs_text.get("0.0", tk.END)
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                messagebox.showinfo("Éxito", "✅ Logs exportados correctamente")
        except Exception as e:
            messagebox.showerror("Error", f"❌ Error exportando logs: {str(e)}")
    
    def on_closing(self):
        """Manejar cierre de aplicación"""
        try:
            # Detener scheduler
            if self.scheduler_running:
                self.stop_scheduler()
            
            # Cancelar descarga activa
            if self.current_job and self.current_job.status == 'running':
                self.current_job.status = 'cancelled'
            
            # Guardar configuración
            save_config()
            
            self.logger.info("👋 Cerrando StreamBus Downloader")
            self.root.destroy()
            
        except Exception as e:
            self.logger.error(f"❌ Error cerrando aplicación: {e}")
            self.root.destroy()
    
    def run(self):
        """Ejecutar aplicación"""
        self.logger.info("🎮 Iniciando interfaz gráfica")
        self.root.mainloop()


    def analyze_downloaded_files(self):
        """
        Analizar archivos descargados y retornar estructura de datos por fecha/hora
        
        Returns:
            dict: {fecha_str: {hora_int: count}}
        """
        try:
            base_dir = get_config('download.base_directory', 'downloads/fotos')
            photos_dir = os.path.join(base_dir, 'security_photos')
            
            if not os.path.exists(photos_dir):
                self.logger.info(f"📁 Directorio de fotos no existe: {photos_dir}")
                return {}
            
            # Patrón para extraer fecha y hora del nombre de archivo
            # Formato: YYYY-MM-DD_hh-mm-ss*.jpg
            pattern = re.compile(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2}).*\.jpg$', re.IGNORECASE)
            
            # Estructura de datos: {fecha: {hora: count}}
            files_data = defaultdict(lambda: defaultdict(int))
            total_files = 0
            
            # Recorrer todos los archivos en todas las subcarpetas
            for root, dirs, files in os.walk(photos_dir):
                for filename in files:
                    match = pattern.match(filename)
                    if match:
                        try:
                            year, month, day, hour, minute, second = match.groups()
                            fecha_str = f"{year}-{month}-{day}"
                            hora_int = int(hour)
                            
                            files_data[fecha_str][hora_int] += 1
                            total_files += 1
                            
                        except ValueError:
                            continue  # Ignorar archivos con formato incorrecto
            
            self.logger.info(f"📊 Análisis completado: {total_files} archivos en {len(files_data)} fechas")
            return dict(files_data)
            
        except Exception as e:
            self.logger.error(f"❌ Error analizando archivos: {e}")
            return {}

    def refresh_files_analysis(self):
        """Actualizar análisis de archivos en background thread"""
        def analyze_async():
            try:
                # Mostrar indicador de carga
                self.root.after(0, lambda: self.files_status_label.configure(text="🔄 Analizando archivos..."))
                self.root.after(0, lambda: self.refresh_analysis_btn.configure(state="disabled"))
                
                # Realizar análisis
                files_data = self.analyze_downloaded_files()
                
                # Actualizar tabla en thread principal
                self.root.after(0, lambda: self.update_files_analysis_table(files_data))
                
            except Exception as e:
                self.logger.error(f"❌ Error en análisis async: {e}")
                self.root.after(0, lambda: self.files_status_label.configure(text="❌ Error en análisis"))
            finally:
                self.root.after(0, lambda: self.refresh_analysis_btn.configure(state="normal"))
        
        threading.Thread(target=analyze_async, daemon=True).start()

    def create_files_analysis_table(self, panel):
        """
        Crear la sección de análisis de archivos en el panel de descarga
        
        Args:
            panel: El panel padre donde agregar la tabla
        """
        # Frame principal para análisis
        analysis_frame = ctk.CTkFrame(panel)
        analysis_frame.pack(fill="both", pady=10, padx=20, expand=True)
        
        # Título y controles
        header_frame = ctk.CTkFrame(analysis_frame)
        header_frame.pack(fill="x", pady=10, padx=10)
        
        ctk.CTkLabel(
            header_frame, 
            text="📊 Análisis de Archivos Descargados", 
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(side="left", padx=10)
        
        # Botón refresh
        self.refresh_analysis_btn = ctk.CTkButton(
            header_frame,
            text="🔄 Actualizar",
            command=self.refresh_files_analysis,
            width=100
        )
        self.refresh_analysis_btn.pack(side="right", padx=10)
        
        # Label de estado
        self.files_status_label = ctk.CTkLabel(header_frame, text="💤 Sin datos")
        self.files_status_label.pack(side="right", padx=(0, 10))
        
        # Frame para la tabla con scroll
        table_container = ctk.CTkFrame(analysis_frame)
        table_container.pack(fill="both", expand=True, pady=(0, 10), padx=10)
        
        # Crear tabla usando Treeview (más adecuado para tablas)
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configurar colores para que combine con customtkinter
        style.configure("Custom.Treeview", 
                    background="#2b2b2b",
                    foreground="white",
                    fieldbackground="#2b2b2b",
                    borderwidth=0)
        style.configure("Custom.Treeview.Heading",
                    background="#1f538d",
                    foreground="white",
                    borderwidth=1)
        
        # Crear Treeview con scrollbars
        table_frame = tk.Frame(table_container)
        table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Definir columnas (Fecha + 24 horas)
        columns = ["Fecha"] + [f"{i:02d}" for i in range(24)]
        
        self.files_tree = ttk.Treeview(table_frame, columns=columns, show="headings", style="Custom.Treeview")
        
        # Configurar encabezados
        self.files_tree.heading("Fecha", text="Fecha")
        self.files_tree.column("Fecha", width=100, minwidth=80)
        
        for hour in range(24):
            col_name = f"{hour:02d}"
            self.files_tree.heading(col_name, text=col_name)
            self.files_tree.column(col_name, width=35, minwidth=30, anchor="center")
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.files_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.files_tree.xview)
        self.files_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack tabla y scrollbars
        self.files_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configurar grid weights
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)
        
        # Información adicional
        info_frame = ctk.CTkFrame(analysis_frame)
        info_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        self.files_summary_label = ctk.CTkLabel(
            info_frame,
            text="📈 Total: 0 archivos en 0 fechas",
            font=ctk.CTkFont(size=12)
        )
        self.files_summary_label.pack(pady=5)
        
        # Cargar datos iniciales
        self.refresh_files_analysis()

    def update_files_analysis_table(self, files_data):
        """
        Actualizar la tabla con nuevos datos de análisis
        
        Args:
            files_data: dict con estructura {fecha: {hora: count}}
        """
        try:
            # Limpiar tabla actual
            for item in self.files_tree.get_children():
                self.files_tree.delete(item)
            
            if not files_data:
                self.files_status_label.configure(text="📭 Sin archivos encontrados")
                self.files_summary_label.configure(text="📈 Total: 0 archivos en 0 fechas")
                return
            
            total_files = 0
            total_dates = len(files_data)
            
            # Ordenar fechas de más reciente a más antigua
            sorted_dates = sorted(files_data.keys(), reverse=True)
            
            # Llenar tabla
            for fecha in sorted_dates:
                hours_data = files_data[fecha]
                
                # Preparar fila: [fecha, count_h0, count_h1, ..., count_h23]
                row_values = [fecha]
                
                for hour in range(24):
                    count = hours_data.get(hour, 0)
                    total_files += count
                    row_values.append(str(count) if count > 0 else "")
                
                # Insertar fila en tabla
                self.files_tree.insert("", "end", values=row_values)
            
            # Actualizar labels de estado
            self.files_status_label.configure(text="✅ Análisis completado")
            self.files_summary_label.configure(
                text=f"📈 Total: {total_files:,} archivos en {total_dates} fechas"
            )
            
            self.logger.info(f"📊 Tabla actualizada: {total_files} archivos, {total_dates} fechas")
            
        except Exception as e:
            self.logger.error(f"❌ Error actualizando tabla: {e}")
            self.files_status_label.configure(text="❌ Error actualizando tabla")

    def get_files_analysis_summary(self):
        """
        Obtener resumen del análisis de archivos para otros usos
        
        Returns:
            dict: Resumen con estadísticas básicas
        """
        try:
            files_data = self.analyze_downloaded_files()
            
            if not files_data:
                return {"total_files": 0, "total_dates": 0, "date_range": None}
            
            total_files = sum(sum(hours.values()) for hours in files_data.values())
            total_dates = len(files_data)
            
            dates = sorted(files_data.keys())
            date_range = f"{dates[0]} → {dates[-1]}" if len(dates) > 1 else dates[0]
            
            # Estadísticas por hora
            hourly_totals = defaultdict(int)
            for date_data in files_data.values():
                for hour, count in date_data.items():
                    hourly_totals[hour] += count
            
            # Hora con más actividad
            peak_hour = max(hourly_totals.items(), key=lambda x: x[1]) if hourly_totals else (0, 0)
            
            return {
                "total_files": total_files,
                "total_dates": total_dates,
                "date_range": date_range,
                "peak_hour": peak_hour[0],
                "peak_hour_count": peak_hour[1],
                "hourly_distribution": dict(hourly_totals)
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error obteniendo resumen: {e}")
            return {"total_files": 0, "total_dates": 0, "date_range": None}


if __name__ == "__main__":
    try:
        app = StreamBusDownloader()
        app.run()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()