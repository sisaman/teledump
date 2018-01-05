import tkinter as tk

class Test(object):
    def __init__(self, root):
        self.laststat=0#just to check multiple <Enter key> press do not delete the data
        self.currString=""
        self.tempString=""
        self.text = tk.Text(root)
        self.text.bind('<Key>', self.stripLine)
        self.text.pack(side=tk.LEFT)
        self.text.focus()
        self.button = tk.Button(root, text = 'Submit', command = self.printData)
        self.button.pack(side=tk.LEFT)

    def stripLine(self, event):
        val=('{k!r}'.format(k = event.char))[1:-1]
        if val=='\\r' and self.laststat==0:
            self.currString=self.tempString
            self.tempString=""
            self.laststat=1
        elif val!='\\r':
            self.tempString+=val
            self.laststat=0


    def printData(self):
        print('Current String is :'+self.currString)
        #print 'temp String is :'+self.tempString

root = tk.Tk()
A = Test(root)
root.mainloop()