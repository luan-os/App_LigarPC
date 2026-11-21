import socket
import time
import threading
import paramiko
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label

# --- CONFIGURAÇÕES DO SEU SERVIDOR ---
PROXMOX_MAC = "00:e0:28:a5:51:e9"
PROXMOX_IP = "192.168.86.200"
VM_ID = "100"
PROXMOX_USER = "root"
PROXMOX_SENHA = "los1998$20"  # Coloque a senha do root do Proxmox

class ProxmoxApp(App):
    def build(self):
        layout = BoxLayout(orientation="vertical", padding=30, spacing=20)

        self.status_label = Label(
            text="Pronto para iniciar o Proxmox e a VM 100",
            font_size="18sp",
            halign="center",
            valign="middle"
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))

        self.botao = Button(
            text="Ligar Proxmox + VM 100",
            font_size="22sp",
            size_hint=(1, 0.35),
            background_color=(0.1, 0.6, 0.3, 1)
        )
        self.botao.bind(on_press=self.iniciar_processo)

        layout.add_widget(self.status_label)
        layout.add_widget(self.botao)
        return layout

    def atualizar_status(self, texto):
        Clock.schedule_once(lambda dt: setattr(self.status_label, 'text', texto))

    def ativar_botao(self, ativo):
        Clock.schedule_once(lambda dt: setattr(self.botao, 'disabled', not ativo))

    def iniciar_processo(self, instance):
        self.ativar_botao(False)
        threading.Thread(target=self.fluxo_proxmox, daemon=True).start()

    def enviar_wol(self, mac):
        mac_limpo = mac.replace(":", "").replace("-", "")
        dados = bytes.fromhex("FF" * 6 + mac_limpo * 16)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(dados, ("255.255.255.255", 9))

    def servidor_online(self, ip, porta=22):
        try:
            with socket.create_connection((ip, porta), timeout=2):
                return True
        except OSError:
            return False

    def fluxo_proxmox(self):
        try:
            # 1. Wake-on-LAN
            self.atualizar_status("1. Enviando sinal Wake-on-LAN para o Proxmox...")
            self.enviar_wol(PROXMOX_MAC)

            # 2 e 3. Aguarda o servidor ligar e a porta SSH (22) responder
            self.atualizar_status(f"2. Aguardando Proxmox ({PROXMOX_IP}) e SSH subirem...")
            tentativas = 0
            while not self.servidor_online(PROXMOX_IP, 22):
                time.sleep(3)
                tentativas += 1
                if tentativas > 60:
                    raise TimeoutError("O servidor demorou muito para responder.")

            # Pequena pausa extra de segurança para o daemon SSH estabilizar
            self.atualizar_status("3. Proxmox online! Conectando via SSH...")
            time.sleep(5)

            # 4. Conecta via SSH e inicia a VM
            cliente = paramiko.SSHClient()
            cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cliente.connect(
                hostname=PROXMOX_IP,
                username=PROXMOX_USER,
                password=PROXMOX_SENHA,
                timeout=10
            )
            
            stdin, stdout, stderr = cliente.exec_command(f"qm start {VM_ID}")
            erro_ssh = stderr.read().decode().strip()
            cliente.close()

            if erro_ssh and "already running" not in erro_ssh:
                self.atualizar_status(f"Aviso do Proxmox: {erro_ssh}")
            else:
                self.atualizar_status(f"Sucesso! Proxmox ligado e VM {VM_ID} iniciada.")

        except Exception as e:
            self.atualizar_status(f"Erro: {str(e)}")
        finally:
            self.ativar_botao(True)

if __name__ == "__main__":
    ProxmoxApp().run()
