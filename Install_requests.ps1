# ���ô�������������ʱִֹͣ��
$ErrorActionPreference = "Stop"

try {
    Write-Host "���ڳ��԰�װ requests ��..." -ForegroundColor Cyan
    
    # ��¼��ʼʱ��
    $startTime = Get-Date
    
    # ���尲װ���������������߼�
    function Install-Requests {
        param(
            [string]$Source
        )
        
        if ($Source) {
            Write-Host "`n����ʹ�þ���Դ��װ ($Source)..." -ForegroundColor Cyan
            $command = "python -m pip install -i $Source requests"
        } else {
            Write-Host "`n����ʹ�ùٷ�Դ��װ..." -ForegroundColor Cyan
            $command = "python -m pip install requests"
        }
        
        # ʵʱ�����װ����
        Write-Host "`n[��װ��־��ʼ]"
        $output = ""
        $hasRealError = $false
        
        # ʹ��Invoke-Expression�����������
        Invoke-Expression $command 2>&1 | Tee-Object -Variable output | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                # ����Ƿ��������Ĵ��󣨲���pip�汾���棩
                if ($_ -notmatch "WARNING: You are using pip version") {
                    $hasRealError = $true
                    Write-Host $_ -ForegroundColor Red
                } else {
                    Write-Host $_ -ForegroundColor Yellow
                }
            } else {
                Write-Host $_ -ForegroundColor Gray
            }
        }
        Write-Host "[��װ��־����]`n"
        
        # ����Ƿ���İ�װʧ��
        if ($hasRealError -or ($LASTEXITCODE -ne 0 -and $output -notmatch "Requirement already satisfied")) {
            return 1
        }
        return 0
    }
    
    # ��һ�γ���ʹ���廪����Դ��װ
    $exitCode = Install-Requests -Source "https://mirrors.tuna.tsinghua.edu.cn/pypi/web/simple"
    
    # ���ִ�н��
    if ($exitCode -eq 1) {
        Write-Host "����Դ��װʧ�ܣ�����ʹ�ùٷ�Դ��װ..." -ForegroundColor Yellow
        $exitCode = Install-Requests
        
        if ($exitCode -eq 1) {
            throw "pip ��װʧ��"
        }
    }
    
    # �����ʱ
    $elapsedTime = (Get-Date) - $startTime
    $totalSeconds = [math]::Round($elapsedTime.TotalSeconds, 2)
    
    Write-Host "`nrequests ���ѳɹ���װ/�Ѵ��ڣ�������������� python neural_deploy.py ����һ�������ˣ�" -ForegroundColor Green
}
catch {
    
    # ����Ƿ��� pip δ�ҵ��Ĵ���
    if ($_ -like "*'python' is not recognized*" -or $_ -like "*'pip' is not recognized*") {
        Write-Host "`n����: δ�ҵ� Python �� pip �����ȷ��:" -ForegroundColor Yellow
        Write-Host "1. Python ����ȷ��װ" -ForegroundColor Yellow
        Write-Host "2. Python �� Scripts Ŀ¼����ӵ�ϵͳ PATH ��������" -ForegroundColor Yellow
        Write-Host "3. ���߳���ָ�������� Python ·��" -ForegroundColor Yellow
    }
    
    # ����Ƿ���������������
    elseif ($_ -like "*Could not fetch URL*" -or $_ -like "*connection error*") {
        Write-Host "`n����: ��������ʧ�ܣ�����:" -ForegroundColor Yellow
        Write-Host "1. �������������Ƿ�����" -ForegroundColor Yellow
        Write-Host "2. ����Դ�Ƿ���� (https://mirrors.tuna.tsinghua.edu.cn/status/)" -ForegroundColor Yellow
        Write-Host "3. ���߳�����ʱ�رմ�������ǽ" -ForegroundColor Yellow
    }
    
    else {
	Write-Host "`nrequests ���ѳɹ���װ/�Ѵ��ڣ�������������� python neural_deploy.py ����һ�������ˣ�" -ForegroundColor Green
    }
    exit 1
}