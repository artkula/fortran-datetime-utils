! Module for date and time operations
module DateTimeUtils
    use DateUtils
    implicit none

    ! DateTime type definition
    type :: DateTime
        integer :: year
        integer :: month
        integer :: day
        integer :: hour
        integer :: minute
        integer :: second
        integer :: millisecond
        character(len=9) :: dayOfWeek
        integer :: timezone
    end type DateTime

    ! Public interfaces
    public :: DateTime, GetDateTime, FormatTime, GetTimezoneInfo, TimeDifference

contains
    ! Get current date and time
    function GetDateTime(dt) result(status)
        type(DateTime), intent(out) :: dt
        integer :: status
        integer :: values(8)

        status = 0
        call date_and_time(VALUES=values)

        dt%year = values(1)
        dt%month = values(2)
        dt%day = values(3)
        dt%timezone = values(4)
        dt%hour = values(5)
        dt%minute = values(6)
        dt%second = values(7)
        dt%millisecond = values(8)

        if (.not. ValidateDate(dt%year, dt%month, dt%day)) then
            status = 1
            return
        end if

        dt%dayOfWeek = GetDayOfWeek(dt%year, dt%month, dt%day)
    end function GetDateTime

    ! Format time as string
    function FormatTime(hour, minute, second, millisecond) result(formattedTime)
        integer, intent(in) :: hour, minute, second
        integer, intent(in), optional :: millisecond
        character(len=12) :: formattedTime
        character(len=2) :: hourStr, minuteStr, secondStr
        character(len=3) :: millisecondStr

        write(hourStr, '(I2.2)') hour
        write(minuteStr, '(I2.2)') minute
        write(secondStr, '(I2.2)') second

        if (present(millisecond)) then
            write(millisecondStr, '(I3.3)') millisecond
            formattedTime = hourStr // ':' // minuteStr // ':' // secondStr // '.' // millisecondStr
        else
            formattedTime = hourStr // ':' // minuteStr // ':' // secondStr
        end if
    end function FormatTime

    ! Format timezone info
    function GetTimezoneInfo(minutesFromUTC) result(timezoneStr)
        integer, intent(in) :: minutesFromUTC
        character(len=12) :: timezoneStr
        integer :: hours, minutes
        character(len=1) :: sign
        character(len=2) :: hourStr, minuteStr

        if (minutesFromUTC < 0) then
            sign = '-'
            hours = abs(minutesFromUTC) / 60
            minutes = abs(minutesFromUTC) - (hours * 60)
        else
            sign = '+'
            hours = minutesFromUTC / 60
            minutes = minutesFromUTC - (hours * 60)
        end if

        write(hourStr, '(I2.2)') hours
        write(minuteStr, '(I2.2)') minutes

        timezoneStr = 'UTC' // sign // hourStr // ':' // minuteStr
    end function GetTimezoneInfo

    ! Calculate time difference
    function TimeDifference(dt1, dt2) result(diffSeconds)
        type(DateTime), intent(in) :: dt1, dt2
        real :: diffSeconds
        integer :: days1, days2
        real :: seconds1, seconds2

        days1 = DaysFromDate(dt1%year, dt1%month, dt1%day)
        days2 = DaysFromDate(dt2%year, dt2%month, dt2%day)

        seconds1 = dt1%hour * 3600 + dt1%minute * 60 + dt1%second + dt1%millisecond / 1000.0
        seconds2 = dt2%hour * 3600 + dt2%minute * 60 + dt2%second + dt2%millisecond / 1000.0

        diffSeconds = (days2 - days1) * 86400.0 + (seconds2 - seconds1)
    end function TimeDifference

    ! Helper function to convert date to days
    function DaysFromDate(year, month, day) result(days)
        integer, intent(in) :: year, month, day
        integer :: days
        integer :: y, i

        y = year - 1900
        days = y * 365

        days = days + (y / 4) - (y / 100) + (y / 400)

        do i = 1, month - 1
            days = days + DAYS_IN_MONTH(i)

            if (i == 2 .and. IsLeapYear(year)) then
                days = days + 1
            end if
        end do

        days = days + day - 1
    end function DaysFromDate
end module DateTimeUtils