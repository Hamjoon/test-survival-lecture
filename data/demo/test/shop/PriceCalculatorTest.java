package shop;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;
class PriceCalculatorTest {
    @Test void appliesDiscount() {
        DiscountService d = mock(DiscountService.class);
        when(d.percentFor("kim")).thenReturn(10);
        assertEquals(900, new PriceCalculator(d).finalPrice("kim", 1000));
    }
    @Test void wrongExpectation() {
        DiscountService d = mock(DiscountService.class);
        when(d.percentFor("lee")).thenReturn(0);
        assertEquals(999, new PriceCalculator(d).finalPrice("lee", 1000));
    }
}
