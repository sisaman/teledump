import csv
import threading
from tqdm import tqdm, trange
from time import sleep
from tkinter import *
from tkinter.ttk import *
from tkinter import filedialog, simpledialog
import jdatetime as jd
import pandas as pd
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import User, Chat, Channel, Message, InputPeerEmpty


def convert65536(s):
    # Converts a string with out-of-range characters in it into a string with codes in it.
    l = list(s)
    i = 0
    while i < len(l):
        o = ord(l[i])
        if o > 65535:
            l[i] = "{" + str(o) + "ū}"
        i += 1
    return "".join(l)


class StdoutRedirector:
    def __init__(self, text_widget: Text):
        self.text_space = text_widget
        self.text_space.bind("<Key>", lambda e: "break")
        self.text_space.bind("<1>", lambda event: text_widget.focus_set())

    def write(self, string: str, ):
        if string.startswith('\r'):
            string = '\n' + string[1:]
            self.delete_line()
        self.text_space.insert('end', string)
        self.text_space.see('end')
        self.text_space.update_idletasks()

    def flush(self):
        self.text_space.update_idletasks()

    def delete_line(self):
        self.text_space.delete("end-1c linestart", "end")


class Application(Frame):
    def __init__(self, master):
        super().__init__(master)

        self.client = None
        self.entities = []

        frame_login = Frame(self)
        label_phone = Label(frame_login, text='Phone Number:')
        self.entry_phone = Entry(frame_login)
        self.entry_phone.bind('<Return>', lambda e: self.login())
        self.button_login = Button(frame_login, text='Login', command=self.login)

        frame_chats = Frame(self)
        label_chats = Label(frame_chats, text='Chat List:')
        scroll_xchats = Scrollbar(frame_chats, orient=HORIZONTAL)
        scroll_ychats = Scrollbar(frame_chats, orient=VERTICAL)
        self.listbox_chats = Listbox(frame_chats, xscrollcommand=scroll_xchats.set, yscrollcommand=scroll_ychats.set,
                                     width='40', selectmode=EXTENDED)
        self.button_select_all = Button(frame_chats, text='All', command=lambda: self.listbox_chats.select_set(0, END))
        self.button_select_none = Button(frame_chats, text='None',
                                         command=lambda: self.listbox_chats.select_clear(0, END))
        self.button_ok = Button(frame_chats, text='OK',
                                command=lambda: threading.Thread(target=self.dump, daemon=True).start())

        frame_console = Frame(self)
        scroll_xconsole = Scrollbar(frame_console, orient=HORIZONTAL)
        scroll_yconsole = Scrollbar(frame_console, orient=VERTICAL)
        self.text_console = Text(frame_console, wrap=NONE, xscrollcommand=scroll_xconsole.set, width='300',
                                 height='100',
                                 yscrollcommand=scroll_yconsole.set, bg='black', fg='white', bd=0)

        frame_login.columnconfigure(1, weight=0)
        frame_login.columnconfigure(2, weight=1)
        frame_login.columnconfigure(3, weight=0)
        frame_login.rowconfigure(1, weight=0)

        label_phone.grid(row=1, column=1)
        self.entry_phone.grid(row=1, column=2, sticky='EW')
        self.button_login.grid(row=1, column=3)

        frame_chats.columnconfigure(1, weight=0)
        frame_chats.columnconfigure(2, weight=0)
        frame_chats.columnconfigure(3, weight=0)
        frame_chats.columnconfigure(4, weight=0)
        frame_chats.rowconfigure(1, weight=0)
        frame_chats.rowconfigure(2, weight=1)
        frame_chats.rowconfigure(3, weight=0)
        frame_chats.rowconfigure(4, weight=0)

        label_chats.grid(row=1, column=1, columnspan=3)
        self.listbox_chats.grid(row=2, column=1, columnspan=3, sticky='NSEW')
        scroll_xchats.grid(row=3, column=1, columnspan=3, sticky='EW')
        scroll_ychats.grid(row=2, column=4, sticky='NS')
        scroll_xchats.config(command=self.listbox_chats.xview)
        scroll_ychats.config(command=self.listbox_chats.yview)
        self.button_select_all.grid(row=4, column=1, sticky='E')
        self.button_select_none.grid(row=4, column=2, sticky='EW')
        self.button_ok.grid(row=4, column=3, sticky='W')

        frame_console.columnconfigure(1, weight=1)
        frame_console.columnconfigure(2, weight=0)
        frame_console.rowconfigure(1, weight=1)
        frame_console.rowconfigure(2, weight=0)

        self.text_console.grid(row=1, column=1, padx=0, sticky='EWSN')
        scroll_xconsole.grid(row=2, column=1, sticky='EW')
        scroll_yconsole.grid(row=1, column=2, sticky='NS')
        scroll_xconsole.config(command=self.text_console.xview)
        scroll_yconsole.config(command=self.text_console.yview)

        self.pack(fill=BOTH, expand=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)
        self.rowconfigure(1, weight=0)
        self.rowconfigure(2, weight=1)

        frame_login.grid(row=1, column=1, sticky='EW', padx=(10, 16), pady=10)
        frame_console.grid(row=2, column=1, sticky='NSWE', padx=(10, 0), pady=(0, 35))
        frame_chats.grid(row=1, column=2, rowspan=2, sticky='NS', padx=10, pady=(23, 10))

        self.redirector = StdoutRedirector(self.text_console)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

        self.entry_phone.focus()
        self.button_ok['state'] = 'disabled'
        self.button_select_all['state'] = 'disabled'
        self.button_select_none['state'] = 'disabled'

    @staticmethod
    def save_file():
        filename = filedialog.asksaveasfilename(defaultextension=".xlsx",
                                                filetypes=(("Excel sheet", "*.xlsx"), ("All Files", "*.*")))
        return filename

    def login(self):
        self.button_login['state'] = 'disabled'
        self.button_ok['state'] = 'disabled'
        self.button_select_all['state'] = 'disabled'
        self.button_select_none['state'] = 'disabled'
        self.text_console.delete('1.0', END)
        self.listbox_chats.delete(0, END)
        self.client = TelegramClient(session=self.entry_phone.get(), api_id=108674,
                                     api_hash='292a4c72c0c026690a8b02fe021d8eaa')
        print('Connecting to Telegram servers...')
        try:
            self.authorize_user()
            threading.Thread(target=self.populate_list()).start()
        except Exception as e:
            print(e)
            print('ERROR: Could not connect to Telegram servers.')
        finally:
            self.button_login['state'] = 'normal'

    def populate_list(self):
        print('Getting chat list...')
        self.list_dialogs()
        self.button_ok['state'] = 'normal'
        self.button_select_all['state'] = 'normal'
        self.button_select_none['state'] = 'normal'

    def dump(self):
        self.button_ok['state'] = 'disabled'
        self.button_select_all['state'] = 'disabled'
        self.button_select_none['state'] = 'disabled'
        try:
            selected_indices = self.listbox_chats.curselection()
            self.entities = [self.entities[int(i)] for i in selected_indices]
            messages = self.get_dialog_history()
            save_to = self.save_file()
            self.dump_messages(messages, save_to)
            print('Saved to %s' % save_to)
            print('=== DONE ===')
        except Exception as e:
            print(e)
            print('ERROR: Could not finish process.')
        finally:
            self.button_login['state'] = 'normal'

    def authorize_user(self):
        user_phone = self.entry_phone.get()
        if not self.client.connect():
            raise Exception('Connection failed.')

        # Then, ensure we're authorized and have access
        if not self.client.is_user_authorized():
            print('First run. Sending code request...')
            self.client.send_code_request(user_phone)

            self_user = None
            while self_user is None:
                # code = self.input('Enter the code you just received: ')
                code = simpledialog.askstring('Login Code', 'Enter the code you just received:')
                try:
                    self_user = self.client.sign_in(user_phone, code)

                # Two-step verification may be enabled
                except SessionPasswordNeededError:
                    pw = simpledialog.askstring('Two-Step Verification',
                                                'Two step verification is enabled. Please enter your password:',
                                                show='*')
                    self_user = self.client.sign_in(password=pw)

        return True

    def list_dialogs(self):
        users = []
        chats = []
        last_date = None
        chunk_size = 100
        while True:
            result = self.client(GetDialogsRequest(
                offset_date=last_date,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=chunk_size
            ))
            if not result.dialogs:
                break
            users.extend(result.users)
            chats.extend(result.chats)
            last_date = min(msg.date for msg in result.messages)
            sleep(.5)

        self.entities = chats + users
        # dialogs, self.entities = self.client.get_dialogs(1000)
        for i, entity in enumerate(self.entities, start=0):
            display_name = Application.get_display_name(entity)
            try:
                self.listbox_chats.insert(i, display_name)
            except:
                self.listbox_chats.insert(i, convert65536(display_name))
        print('Chat list ready. Please select dialogs from the list and press OK.')

    # def select_dialog(self, entities):
    #     print('\n')
    #     str_ids = self.input('Select dialog IDs (separate by space): ').split()
    #     ids = [int(i if i else 0) - 1 for i in str_ids]
    #     return [entities[i] for i in ids]

    def get_dialog_history(self):
        window_size = 100
        result = []
        e = 0
        for entity in self.entities:
            e += 1
            history = []
            total, _, _ = self.client.get_message_history(entity, limit=1)
            print('"(%d/%d) %s"' % (e, len(self.entities), self.get_display_name(entity)))
            with tqdm(total=total, bar_format='  {percentage:3.0f}%  |{bar}|  {n_fmt}/{total_fmt}', ncols=100) as bar:
                for offset in range(0, total, window_size):
                    while True:
                        try:
                            count, messages, senders = self.client.get_message_history(entity, limit=window_size,
                                                                                       add_offset=offset)
                            for i in range(len(messages)):
                                messages[i].from_id = senders[i].id
                                messages[i].sender_name = self.get_display_name(senders[i])
                                messages[i].phone = senders[i].phone if isinstance(senders[i], User) else None
                                messages[i].username = senders[i].username
                        except FloodWaitError as e:
                            print(e)
                            sleep(e.seconds + 1)
                            print('continue')
                            continue
                        break

                    history += messages
                    sleep(1)
                    bar.update(len(messages))
                result += history
        return result

    @staticmethod
    def dump_messages(messages, filename):
        id_map = {}
        global id_count
        id_count = 0

        def get_msg_id(sender_id, date):
            global id_count
            if (sender_id, date) in id_map:
                return id_map[(sender_id, date)]
            else:
                id_map[(sender_id, date)] = id_count
                id_count += 1
                return id_count - 1

        print('Saving received data...')
        with open('temp.csv', 'w', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(('MsgID', 'Date', 'Time', 'SenderID', 'Name', 'Username', 'Phone', 'Message'))
            for message in messages:
                if isinstance(message, Message):
                    sender_id = message.from_id
                    sender_name = message.sender_name
                    username = message.username
                    phone = message.phone
                    msg_text = message.message
                    datetime = message.date
                    jdate = jd.datetime.fromgregorian(year=datetime.year, month=datetime.month, day=datetime.day)
                    date = jdate.strftime('%y/%m/%d')
                    time = datetime.strftime('%H:%M:%S')
                    # fwd_id = None
                    if message.fwd_from:
                        msg_id = get_msg_id(message.fwd_from.from_id, message.fwd_from.date)
                    else:
                        msg_id = get_msg_id(message.from_id, message.date)
                    writer.writerow((msg_id, date, time, sender_id, sender_name, username, phone, msg_text))

        data = pd.read_csv('temp.csv', index_col=False, parse_dates=['Time'], dtype={'Phone': 'str'})
        writer = pd.ExcelWriter(filename)
        data.to_excel(writer, 'Sheet1', index=False)
        writer.save()

    @staticmethod
    def get_display_name(entity):
        """Gets the input peer for the given "entity" (user, chat or channel)
           Returns None if it was not found"""
        if isinstance(entity, User):
            if entity.last_name and entity.first_name:
                return '{} {}'.format(entity.first_name, entity.last_name)
            elif entity.first_name:
                return entity.first_name
            elif entity.last_name:
                return entity.last_name
            else:
                return '(No name)'

        if isinstance(entity, Chat) or isinstance(entity, Channel):
            return entity.title

        return '(unknown)'


if __name__ == '__main__':
    root = Tk()
    root.title('TeleDump')
    # root.iconbitmap('infomax.ico')
    # root.geometry("650x400+300+300")
    root.state('zoomed')
    app = Application(root)
    root.protocol("WM_DELETE_WINDOW", lambda : root.destroy())
    root.mainloop()
    root.destroy()
