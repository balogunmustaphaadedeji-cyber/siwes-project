using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Windows.Forms;

namespace SmartOfficeLauncher;

internal static class Program
{
    [STAThread]
    static void Main()
    {
        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
    }
}

public class MainForm : Form
{
    private readonly Label status = new();
    private readonly Button startButton = new();
    private readonly Button stopButton = new();
    private Process? cameraProcess;
    private readonly string pythonFolder;

    public MainForm()
    {
        Text = "Smart Office | Attendance System";
        Width = 720;
        Height = 460;
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = Color.FromArgb(244, 247, 251);
        Font = new Font("Segoe UI", 10);

        // Set this to the absolute path of the extracted project's python folder.
        pythonFolder = Path.GetFullPath(Path.Combine(AppContext.BaseDirectory,
            "..", "..", "..", "..", "..", "python"));

        var heading = new Label {
            Text = "SMART OFFICE",
            Font = new Font("Segoe UI", 22, FontStyle.Bold),
            ForeColor = Color.FromArgb(25, 51, 87),
            AutoSize = true, Location = new Point(28, 24)
        };
        var subtitle = new Label {
            Text = "Face Recognition & Attendance Monitoring",
            Font = new Font("Segoe UI", 11),
            ForeColor = Color.FromArgb(90, 105, 125),
            AutoSize = true, Location = new Point(31, 68)
        };
        status.Text = "Status: Camera stopped";
        status.AutoSize = true;
        status.Location = new Point(32, 130);
        status.Font = new Font("Segoe UI", 12, FontStyle.Bold);

        startButton.Text = "Start Webcam Recognition";
        startButton.Location = new Point(32, 175);
        startButton.Size = new Size(250, 46);
        startButton.Click += (_, _) => StartCamera();

        stopButton.Text = "Stop Camera";
        stopButton.Location = new Point(300, 175);
        stopButton.Size = new Size(150, 46);
        stopButton.Enabled = false;
        stopButton.Click += (_, _) => StopCamera();

        var registerButton = new Button {
            Text = "Register Person",
            Location = new Point(32, 240), Size = new Size(200, 42)
        };
        registerButton.Click += (_, _) => RunPythonTool("register_person.py");

        var exportButton = new Button {
            Text = "Export Attendance CSV",
            Location = new Point(246, 240), Size = new Size(220, 42)
        };
        exportButton.Click += (_, _) => RunPythonTool("export_attendance.py");

        var note = new Label {
            Text = "The live webcam opens in a separate OpenCV window.\\nRegister consenting participants before starting recognition.",
            Location = new Point(32, 315), Size = new Size(630, 55),
            ForeColor = Color.FromArgb(75, 90, 110)
        };

        Controls.AddRange(new Control[] { heading, subtitle, status, startButton, stopButton,
            registerButton, exportButton, note });
        FormClosing += (_, _) => StopCamera();
    }

    private string FindPythonFolder()
    {
        // Look for the project folder near the current directory or ask user to select it.
        string[] candidates = {
            Path.GetFullPath(Path.Combine(Environment.CurrentDirectory, "python")),
            Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "..", "python"))
        };
        foreach (var candidate in candidates)
            if (File.Exists(Path.Combine(candidate, "attendance_camera.py")))
                return candidate;

        using var dialog = new FolderBrowserDialog {
            Description = "Select the extracted project's python folder (the folder containing attendance_camera.py)"
        };
        if (dialog.ShowDialog(this) == DialogResult.OK &&
            File.Exists(Path.Combine(dialog.SelectedPath, "attendance_camera.py")))
            return dialog.SelectedPath;
        throw new DirectoryNotFoundException("Could not find the python folder.");
    }

    private string PythonExe(string folder)
    {
        var venvPython = Path.Combine(folder, ".venv", "Scripts", "python.exe");
        return File.Exists(venvPython) ? venvPython : "python";
    }

    private void StartCamera()
    {
        try
        {
            var folder = FindPythonFolder();
            cameraProcess = new Process {
                StartInfo = new ProcessStartInfo {
                    FileName = PythonExe(folder),
                    Arguments = "\"attendance_camera.py\"",
                    WorkingDirectory = folder,
                    UseShellExecute = false,
                    CreateNoWindow = false
                },
                EnableRaisingEvents = true
            };
            cameraProcess.Start();
            status.Text = "Status: Recognition process started";
            startButton.Enabled = false;
            stopButton.Enabled = true;
            cameraProcess.Exited += (_, _) => BeginInvoke(new Action(() => {
                status.Text = "Status: Camera stopped";
                startButton.Enabled = true;
                stopButton.Enabled = false;
                cameraProcess?.Dispose();
                cameraProcess = null;
            }));
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Unable to start camera", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }

    private void StopCamera()
    {
        if (cameraProcess is { HasExited: false })
        {
            try { cameraProcess.Kill(true); cameraProcess.WaitForExit(2000); }
            catch { }
        }
        cameraProcess?.Dispose();
        cameraProcess = null;
        status.Text = "Status: Camera stopped";
        startButton.Enabled = true;
        stopButton.Enabled = false;
    }

    private void RunPythonTool(string script)
    {
        try
        {
            var folder = FindPythonFolder();
            var file = Path.Combine(folder, script);
            if (!File.Exists(file)) throw new FileNotFoundException("Script not found", file);
            Process.Start(new ProcessStartInfo {
                FileName = PythonExe(folder),
                Arguments = $"\"{script}\"",
                WorkingDirectory = folder,
                UseShellExecute = true
            });
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Unable to run tool", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
    }
}
