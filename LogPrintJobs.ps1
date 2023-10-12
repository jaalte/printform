# PowerShell Script to log print jobs
# Save as LogPrintJobs.ps1

# Output File
$OutputFile = "C:\Users\dvchort\Desktop\printform\print-job-log.csv"

# Header
if (-Not (Test-Path $OutputFile)) {
    "Timestamp, User, DocumentName, Printer" | Out-File $OutputFile
}

# Run indefinitely
while ($true) {
    # Retrieve print events
    $printEvents = Get-WinEvent -LogName 'Microsoft-Windows-PrintService/Operational' -MaxEvents 10 | Where-Object { $_.ID -eq 307 }

    foreach ($event in $printEvents) {
        $timestamp = $event.TimeCreated
        $user = $event.Properties[1].Value
        $docName = $event.Properties[2].Value
        $printer = $event.Properties[3].Value

        # Output to CSV
        "$timestamp, $user, $docName, $printer" | Out-File -Append $OutputFile
    }

    # Sleep for 60 seconds
    Start-Sleep -Seconds 60
}
