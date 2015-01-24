"""
Created on Sep 29, 2014
Copyright (c) 2014
Harvard FAS Research Computing
All rights reserved.

@author: Aaron Kitzmiller
"""

import unittest
import os, sys, time
import subprocess
from stat import S_IXUSR, S_IWUSR, S_IRUSR
from command import RunLog, ShellRunner, DefaultFileLogger, Command
import yaml

import datetime

class Test(unittest.TestCase):
        
    def setUp(self):
        
        self.activatevenv = ""
        if "VIRTUAL_ENV" in os.environ:
            self.activatevenv = "source %s/bin/activate && " % os.environ["VIRTUAL_ENV"]

        script = '''
#!/bin/bash
 
n="0"
 
while [[ $n -lt 40 ]]
do
  echo "All work and no play makes Jack a dull boy" >&2
  echo "All work and no play makes Jane a dull girl"
  sleep 2 
  n=$[$n + 1]
 
done
        '''.strip()
         
        with open("long.sh","w") as scriptfile:
            scriptfile.write(script)

        ## Fail before ending and return non-zero
        script = '''
#!/bin/bash
 
n="0"
 
while [[ $n -lt 10 ]]
do
  echo "All work and no play makes Jane a dull girl"
  sleep 2 
  n=$[$n + 1]
done
echo "Fail!" >&2
exit 2
        '''.strip()
         
        with open("fail.sh","w") as scriptfile:
            scriptfile.write(script)


        try:
            os.remove("stdout")
        except Exception:
            pass

        try:
            os.remove("stderr")
        except Exception:
            pass

        try:
            os.remove("test.yaml")
        except Exception:
            pass

    
    def tearDown(self):
        pass
    
    def testRunLogger(self):
         
        # Create a RunSet and save it
        runset = []
        runset.append(RunLog(   jobid='1234',
                                hostname='localhost',
                                cmdstring="echo 'Hello'",
                                starttime=datetime.datetime.now())
                      )
        logger = DefaultFileLogger()
        runsetfilename = logger.saveRunSet(runset, 'testrunset')
        runsettext = open(runsetfilename,'r').readlines()
         
        # Check file text contents
        self.assertTrue("jobid: '1234'" in runsettext[0],runsettext)
        self.assertTrue("cmdstring: echo 'Hello'" in runsettext[0],runsettext)
        self.assertTrue("hostname: localhost" in runsettext[0],runsettext)
        self.assertTrue("starttime: '2015-" in runsettext[0],runsettext)
         
        # Retrieve as RunSet
        runset = logger.getRunSet('testrunset')
        self.assertTrue(runset[0]['jobid'] == '1234')
        self.assertTrue(runset[0]['cmdstring'] == "echo 'Hello'")
        self.assertTrue(runset[0]['hostname'] == "localhost")
         
        # Update existing RunSet
        runset[0]['endtime'] = datetime.datetime.now()
        logger.saveRunSet(runset,'testrunset')
         
        runset2 = logger.getRunSet('testrunset')
        self.assertTrue(runset2[0]['jobid'] == '1234')
        self.assertTrue(runset2[0]['endtime'].year == datetime.datetime.now().year)
        self.assertTrue(runset2[0]['endtime'].month == datetime.datetime.now().month)
        self.assertTrue(runset2[0]['endtime'].day == datetime.datetime.now().day)
 
        # Missing required field
        self.assertRaises(Exception, lambda: RunLog(jobid='1234', hostname='localhost',cmdstring="echo 'Hello'"))
                                
         
    def testCommand(self):
         
        # Verify proper command string construction
        print "Testing simple commands"
        cmd = Command("echo 'Hello'")
        self.assertTrue(cmd.composeCmdString() == "echo 'Hello'")
        cmd = Command("echo","'Hello'")
        self.assertTrue(cmd.composeCmdString() == "echo 'Hello'")
        cmd = Command("echo","-n","'Hello'")
        self.assertTrue(cmd.composeCmdString() == "echo -n 'Hello'")
        cmd = Command("echo","'Hello'",n=True)
        self.assertTrue(cmd.composeCmdString() == "echo 'Hello' -n", cmd.composeCmdString())
        cmd = Command("test",arg1="value1",arg2="value2",arg3="value3")
        self.assertTrue(cmd.composeCmdString() == "test --arg1=value1 --arg2=value2 --arg3=value3",cmd.composeCmdString())
         
     
    def testShellRunner(self):
          
        ## Direct string execution, stdout string
        r = ShellRunner()
        h = r.run(Command("echo 'Hello'"))
        self.assertEqual(h.stdoutstr, "Hello\n")
        self.assertEqual(h.stderrstr,"")
          
        ## Direct string execution, stderr string
        h = r.run(Command("cat nosuchfile"))
        self.assertEqual(h.stdoutstr,"")
        self.assertEqual(h.stderrstr,"cat: nosuchfile: No such file or directory\n")
         
        ## Run a long binary that prints to both stderr and stdout
             
        os.chmod("long.sh", S_IXUSR | S_IRUSR | S_IWUSR)
        print "Running long.sh..."
        h = r.run(Command("bash long.sh"))
        stdoutstr = h.stdoutstr
        stderrstr = h.stderrstr
        print "Done."
           
        self.assertEqual(len(stdoutstr.split("\n")), 41, len(stdoutstr.split("\n")))
        self.assertEqual(len(stderrstr.split("\n")), 41, len(stderrstr.split("\n")))
           
        ## Direct string execution, stdout iterator
        print "Starting long.sh..."
        h = r.run(Command("bash long.sh"))
        stdout = h.stdout
        lines = []
        while h.checkStatus() is None:
            where = stdout.tell()
            line = stdout.readline()
            if not line:
                time.sleep(1)
                stdout.seek(where)
            else:
                lines.append(line.strip())
                   
        self.assertEquals(len(lines), 40, lines)
        self.assertTrue('Jane a dull girl' in lines[0], lines[0])
                   
        ## Direct string execution, stderr iterator
        print "Starting long.sh..."
        h = r.run(Command("bash long.sh"))
        stderr = h.stderr
        lines = []
        while h.checkStatus() is None:
            where = stderr.tell()
            line = stderr.readline()
            if not line:
                time.sleep(1)
                stderr.seek(where)
            else:
                lines.append(line.strip())
                   
        self.assertEquals(len(lines), 40, lines)
        self.assertTrue('Jack a dull boy' in lines[0], lines[0])
         
             
        os.chmod("fail.sh", S_IXUSR | S_IRUSR | S_IWUSR)
        print "Running fail.sh..."
        h = r.run(Command("bash fail.sh"))
        stdoutstr = h.stdoutstr
        stderrstr = h.stderrstr
        self.assertTrue(len(stdoutstr.split("\n")) == 11,len(stdoutstr.split("\n")))
        self.assertTrue('Fail!' in stderrstr,stderrstr)
        
        
#    def testRcx(self):
#        """
#        Test the rcx.py tool that launches a job.  Then connect to the 
#        stderr / stdout stream of that job using the runset information
#        """
#        
#        # Test with minimum parameters (execute command and return stdout)
#        cmdstring = "%s../../bin/rcx.py echo 'Hello'" % self.activatevenv    
#        p  = subprocess.Popen(cmdstring,shell=True,stdout=subprocess.PIPE)
#        (out,err) = p.communicate()
#        self.assertTrue("Hello" in out,"Cmdstring: %s stdout: %s stderr: %s" % (cmdstring,out,err))
#         
#        # Set stderr and stdout files; check contents
#         
#        cmdstring = "%s../../bin/rcx.py --rcx-stderr=stderr --rcx-stdout=stdout bash fail.sh" % self.activatevenv
#        p  = subprocess.Popen(cmdstring,shell=True,stdout=subprocess.PIPE)
#        (out,err) = p.communicate()
#        out = []
#        with open("stdout","r") as o:
#            out = o.read()
#        self.assertTrue("All work and no play makes Jane a dull girl" in out,out)
#        err = []
#        with open("stderr","r") as e:
#            err = e.read()
#        self.assertTrue("Fail!" in err,err)
#         
#        # Set runsetname and runsetpath; get corresponding runset yaml file directly
#         
#    def testRcxSubmit(self):
#        """
#        Tests rcx.py in submit mode (run and terminate)
#        """
#        
#        cwd = os.getcwd()
#        testyamlfile = "test.yaml"
#        cmdstring = "%s../../bin/rcx.py --rcx-jobtype=submit --rcx-stderr=stderr --rcx-stdout=stdout --rcx-runsetpath=%s --rcx-runsetname=test bash fail.sh" % (self.activatevenv, cwd)
#        p  = subprocess.Popen(cmdstring,shell=True,stdout=subprocess.PIPE)
#        pid = p.pid
#        count = 0
#        runsetdata = None
#        while count < 5 and runsetdata is None:            
#            time.sleep(1)
#            try:
#                runsetdata = yaml.safe_load(open(os.path.join(cwd,testyamlfile),'r'))
#            except Exception:
#                pass
#        if count == 5 and runsetdata is None:
#            raise Exception("Can't open yaml file %s" % testyamlfile)
#        
#        jobid = runsetdata[0]['jobid']
#        self.assertTrue(runsetdata[0]['stderrfile'] == os.path.join(cwd,'stderr'),runsetdata[0])
#        self.assertTrue(runsetdata[0]['stdoutfile'] == os.path.join(cwd,'stdout'),runsetdata[0])
#        self.assertTrue(runsetdata[0]['cmdstring'] == 'bash fail.sh',runsetdata[0])
#        self.assertTrue(runsetdata[0]['runner'] == 'shellrunner.ShellRunner',runsetdata[0])
#
#        stdout = open("./stdout","r")
#        lines = []
#        devnull = open(os.devnull,'w')
#        checkcmd = "kill -0 %d" % jobid
#        print "Checkcmd %s" % checkcmd
#        returnval = subprocess.call(checkcmd,shell=True,stdout=devnull,stderr=subprocess.STDOUT)
#        print "Return val %d" % returnval
#        while returnval == 0:
#            where = stdout.tell()
#            line = stdout.readline()
#            if not line:
#                time.sleep(1)
#                stdout.seek(where)
#            else:
#                lines.append(line.strip())
#                print line.strip()
#            returnval = subprocess.call(checkcmd,shell=True,stdout=devnull,stderr=subprocess.STDOUT)
#        self.assertTrue(len(lines) == 10,lines)
#        self.assertTrue("All work and no play makes Jane a dull girl" in lines[0], lines[0])
#        
#        # Launch long running job and detach.  get stdout from stdout file.
#        
        
if __name__ == "__main__":
        unittest.main()    
